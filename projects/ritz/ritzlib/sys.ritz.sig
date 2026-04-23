{
  "source_hash": "4f015fb1586d6574",
  "functions": {
    "sys_yield": {
      "hash": "ed69b1156f0f39c7",
      "sig_hash": "ffec476e30b82064",
      "ir": ""
    },
    "sys_getpid": {
      "hash": "66c4578f2ebb2ee8",
      "sig_hash": "588a8c119884a3f1",
      "ir": "define i32 @\"sys_getpid\"() alignstack(16) !dbg !17\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 39), !dbg !83\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !83\n  ret i32 %\".3\", !dbg !83\n}"
    },
    "sys_spawn": {
      "hash": "2a2bf73a79c4da99",
      "sig_hash": "addaef2cce1eb030",
      "ir": ""
    },
    "sys_spawn_args": {
      "hash": "3f4e162ee3e5e7db",
      "sig_hash": "8b6abe2b0cfa7f38",
      "ir": ""
    },
    "sys_wait": {
      "hash": "089a78819c1054cb",
      "sig_hash": "f19451cf66d7c8a6",
      "ir": ""
    },
    "sys_readdir": {
      "hash": "9daf639b1f5a4849",
      "sig_hash": "13771e780c7ede35",
      "ir": ""
    },
    "sys_acpi_poweroff": {
      "hash": "9223e05ebc04ddb3",
      "sig_hash": "1e28fcd1df20701f",
      "ir": ""
    },
    "sys_getcwd": {
      "hash": "19661c15aec69e51",
      "sig_hash": "ee8adeea78fcf1a2",
      "ir": "define i64 @\"sys_getcwd\"(i8* %\"buf.arg\", i64 %\"size.arg\") alignstack(16) !dbg !18\n{\nentry:\n  %\"buf\" = alloca i8*\n  store i8* %\"buf.arg\", i8** %\"buf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"buf\", metadata !85, metadata !7), !dbg !86\n  %\"size\" = alloca i64\n  store i64 %\"size.arg\", i64* %\"size\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"size\", metadata !87, metadata !7), !dbg !86\n  %\".8\" = load i8*, i8** %\"buf\", !dbg !88\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !88\n  %\".10\" = load i64, i64* %\"size\", !dbg !88\n  %\".11\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 79, i64 %\".9\", i64 %\".10\"), !dbg !88\n  ret i64 %\".11\", !dbg !88\n}"
    },
    "sys_chdir": {
      "hash": "d476e47ec993be54",
      "sig_hash": "c93f60b133fe331b",
      "ir": "define i32 @\"sys_chdir\"(i8* %\"path.arg\") alignstack(16) !dbg !19\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !89, metadata !7), !dbg !90\n  %\".5\" = load i8*, i8** %\"path\", !dbg !91\n  %\".6\" = ptrtoint i8* %\".5\" to i64 , !dbg !91\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 80, i64 %\".6\"), !dbg !91\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !91\n  ret i32 %\".8\", !dbg !91\n}"
    },
    "sys_spawn_ex": {
      "hash": "b02285e3cf14d78e",
      "sig_hash": "6f7068da7b38384a",
      "ir": ""
    },
    "sys_pipe": {
      "hash": "051074a31b8731c2",
      "sig_hash": "bb2e0567030e9d22",
      "ir": "define i32 @\"sys_pipe\"(i32* %\"pipefd.arg\") alignstack(16) !dbg !20\n{\nentry:\n  %\"pipefd\" = alloca i32*\n  store i32* %\"pipefd.arg\", i32** %\"pipefd\"\n  call void @\"llvm.dbg.declare\"(metadata i32** %\"pipefd\", metadata !93, metadata !7), !dbg !94\n  %\".5\" = load i32*, i32** %\"pipefd\", !dbg !95\n  %\".6\" = ptrtoint i32* %\".5\" to i64 , !dbg !95\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 22, i64 %\".6\"), !dbg !95\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !95\n  ret i32 %\".8\", !dbg !95\n}"
    },
    "sys_input_poll": {
      "hash": "9c8dc2c22ee9fa5a",
      "sig_hash": "bd11e878924f2e49",
      "ir": ""
    },
    "sys_input_read": {
      "hash": "5c90c8e28b6ba262",
      "sig_hash": "de1bdcc4ef5665b9",
      "ir": ""
    },
    "sys_mmap": {
      "hash": "ab8dce7507a6298b",
      "sig_hash": "ee36e41c896712d9",
      "ir": "define i8* @\"sys_mmap\"(i64 %\"addr.arg\", i64 %\"length.arg\", i32 %\"prot.arg\", i32 %\"flags.arg\", i32 %\"fd.arg\", i64 %\"offset.arg\") alignstack(16) !dbg !21\n{\nentry:\n  %\"addr\" = alloca i64\n  store i64 %\"addr.arg\", i64* %\"addr\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"addr\", metadata !96, metadata !7), !dbg !97\n  %\"length\" = alloca i64\n  store i64 %\"length.arg\", i64* %\"length\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"length\", metadata !98, metadata !7), !dbg !97\n  %\"prot\" = alloca i32\n  store i32 %\"prot.arg\", i32* %\"prot\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"prot\", metadata !99, metadata !7), !dbg !97\n  %\"flags\" = alloca i32\n  store i32 %\"flags.arg\", i32* %\"flags\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"flags\", metadata !100, metadata !7), !dbg !97\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !101, metadata !7), !dbg !97\n  %\"offset\" = alloca i64\n  store i64 %\"offset.arg\", i64* %\"offset\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"offset\", metadata !102, metadata !7), !dbg !97\n  %\".20\" = load i64, i64* %\"addr\", !dbg !103\n  %\".21\" = load i64, i64* %\"length\", !dbg !103\n  %\".22\" = load i32, i32* %\"prot\", !dbg !103\n  %\".23\" = sext i32 %\".22\" to i64 , !dbg !103\n  %\".24\" = load i32, i32* %\"flags\", !dbg !103\n  %\".25\" = sext i32 %\".24\" to i64 , !dbg !103\n  %\".26\" = load i32, i32* %\"fd\", !dbg !103\n  %\".27\" = sext i32 %\".26\" to i64 , !dbg !103\n  %\".28\" = load i64, i64* %\"offset\", !dbg !103\n  %\".29\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},{r8},{r9},~{rcx},~{r11},~{memory}\"(i64 9, i64 %\".20\", i64 %\".21\", i64 %\".23\", i64 %\".25\", i64 %\".27\", i64 %\".28\"), !dbg !103\n  %\".30\" = inttoptr i64 %\".29\" to i8* , !dbg !103\n  ret i8* %\".30\", !dbg !103\n}"
    },
    "sys_munmap": {
      "hash": "1979756d5a488b66",
      "sig_hash": "4bc111f7b41be15c",
      "ir": "define i32 @\"sys_munmap\"(i8* %\"addr.arg\", i64 %\"length.arg\") alignstack(16) !dbg !22\n{\nentry:\n  %\"addr\" = alloca i8*\n  store i8* %\"addr.arg\", i8** %\"addr\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"addr\", metadata !104, metadata !7), !dbg !105\n  %\"length\" = alloca i64\n  store i64 %\"length.arg\", i64* %\"length\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"length\", metadata !106, metadata !7), !dbg !105\n  %\".8\" = load i8*, i8** %\"addr\", !dbg !107\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !107\n  %\".10\" = load i64, i64* %\"length\", !dbg !107\n  %\".11\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 11, i64 %\".9\", i64 %\".10\"), !dbg !107\n  %\".12\" = trunc i64 %\".11\" to i32 , !dbg !107\n  ret i32 %\".12\", !dbg !107\n}"
    },
    "sys_stat2": {
      "hash": "3fb3c460ba2bbade",
      "sig_hash": "dba829ba124a9707",
      "ir": "define i32 @\"sys_stat2\"(i8* %\"path.arg\", %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\") alignstack(16) !dbg !23\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !108, metadata !7), !dbg !109\n  %\"statbuf\" = alloca %\"struct.ritz_module_1.Stat\"*\n  store %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\", %\"struct.ritz_module_1.Stat\"** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Stat\"** %\"statbuf\", metadata !112, metadata !7), !dbg !109\n  %\".8\" = load i8*, i8** %\"path\", !dbg !113\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !113\n  %\".10\" = load %\"struct.ritz_module_1.Stat\"*, %\"struct.ritz_module_1.Stat\"** %\"statbuf\", !dbg !113\n  %\".11\" = ptrtoint %\"struct.ritz_module_1.Stat\"* %\".10\" to i64 , !dbg !113\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 4, i64 %\".9\", i64 %\".11\"), !dbg !113\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !113\n  ret i32 %\".13\", !dbg !113\n}"
    },
    "sys_fstat2": {
      "hash": "7d2910c4fe581343",
      "sig_hash": "b29835d92e0b2b2d",
      "ir": "define i32 @\"sys_fstat2\"(i32 %\"fd.arg\", %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\") alignstack(16) !dbg !24\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !114, metadata !7), !dbg !115\n  %\"statbuf\" = alloca %\"struct.ritz_module_1.Stat\"*\n  store %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\", %\"struct.ritz_module_1.Stat\"** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Stat\"** %\"statbuf\", metadata !116, metadata !7), !dbg !115\n  %\".8\" = load i32, i32* %\"fd\", !dbg !117\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !117\n  %\".10\" = load %\"struct.ritz_module_1.Stat\"*, %\"struct.ritz_module_1.Stat\"** %\"statbuf\", !dbg !117\n  %\".11\" = ptrtoint %\"struct.ritz_module_1.Stat\"* %\".10\" to i64 , !dbg !117\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 5, i64 %\".9\", i64 %\".11\"), !dbg !117\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !117\n  ret i32 %\".13\", !dbg !117\n}"
    },
    "sys_lstat2": {
      "hash": "f6c0d5d57c04fb2a",
      "sig_hash": "c8a10d4cacffcca8",
      "ir": "define i32 @\"sys_lstat2\"(i8* %\"path.arg\", %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\") alignstack(16) !dbg !25\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !118, metadata !7), !dbg !119\n  %\"statbuf\" = alloca %\"struct.ritz_module_1.Stat\"*\n  store %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\", %\"struct.ritz_module_1.Stat\"** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Stat\"** %\"statbuf\", metadata !120, metadata !7), !dbg !119\n  %\".8\" = load i8*, i8** %\"path\", !dbg !121\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !121\n  %\".10\" = load %\"struct.ritz_module_1.Stat\"*, %\"struct.ritz_module_1.Stat\"** %\"statbuf\", !dbg !121\n  %\".11\" = ptrtoint %\"struct.ritz_module_1.Stat\"* %\".10\" to i64 , !dbg !121\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 6, i64 %\".9\", i64 %\".11\"), !dbg !121\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !121\n  ret i32 %\".13\", !dbg !121\n}"
    },
    "at_fdcwd": {
      "hash": "794e59f2c2fc51d5",
      "sig_hash": "692c8512c2111e23",
      "ir": "define i32 @\"at_fdcwd\"() alignstack(16) !dbg !26\n{\nentry:\n  %\".2\" = sub i64 0, 100, !dbg !122\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !122\n  ret i32 %\".3\", !dbg !122\n}"
    },
    "sys_read": {
      "hash": "e5a05419b4ae583b",
      "sig_hash": "5f03fd03be67a0c6",
      "ir": "define i64 @\"sys_read\"(i32 %\"fd.arg\", i8* %\"buf.arg\", i64 %\"count.arg\") alignstack(16) !dbg !27\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !123, metadata !7), !dbg !124\n  %\"buf\" = alloca i8*\n  store i8* %\"buf.arg\", i8** %\"buf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"buf\", metadata !125, metadata !7), !dbg !124\n  %\"count\" = alloca i64\n  store i64 %\"count.arg\", i64* %\"count\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"count\", metadata !126, metadata !7), !dbg !124\n  %\".11\" = load i32, i32* %\"fd\", !dbg !127\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !127\n  %\".13\" = load i8*, i8** %\"buf\", !dbg !127\n  %\".14\" = ptrtoint i8* %\".13\" to i64 , !dbg !127\n  %\".15\" = load i64, i64* %\"count\", !dbg !127\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 0, i64 %\".12\", i64 %\".14\", i64 %\".15\"), !dbg !127\n  ret i64 %\".16\", !dbg !127\n}"
    },
    "sys_write": {
      "hash": "ef9628165cd5a57b",
      "sig_hash": "f7c9e60092ca93ca",
      "ir": "define i64 @\"sys_write\"(i32 %\"fd.arg\", i8* %\"buf.arg\", i64 %\"count.arg\") alignstack(16) !dbg !28\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !128, metadata !7), !dbg !129\n  %\"buf\" = alloca i8*\n  store i8* %\"buf.arg\", i8** %\"buf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"buf\", metadata !130, metadata !7), !dbg !129\n  %\"count\" = alloca i64\n  store i64 %\"count.arg\", i64* %\"count\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"count\", metadata !131, metadata !7), !dbg !129\n  %\".11\" = load i32, i32* %\"fd\", !dbg !132\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !132\n  %\".13\" = load i8*, i8** %\"buf\", !dbg !132\n  %\".14\" = ptrtoint i8* %\".13\" to i64 , !dbg !132\n  %\".15\" = load i64, i64* %\"count\", !dbg !132\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 1, i64 %\".12\", i64 %\".14\", i64 %\".15\"), !dbg !132\n  ret i64 %\".16\", !dbg !132\n}"
    },
    "sys_open": {
      "hash": "66834bbd60f6749b",
      "sig_hash": "e991aeb07a042029",
      "ir": "define i32 @\"sys_open\"(i8* %\"path.arg\", i32 %\"flags.arg\") alignstack(16) !dbg !29\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !133, metadata !7), !dbg !134\n  %\"flags\" = alloca i32\n  store i32 %\"flags.arg\", i32* %\"flags\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"flags\", metadata !135, metadata !7), !dbg !134\n  %\".8\" = load i8*, i8** %\"path\", !dbg !136\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !136\n  %\".10\" = load i32, i32* %\"flags\", !dbg !136\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !136\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 2, i64 %\".9\", i64 %\".11\"), !dbg !136\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !136\n  ret i32 %\".13\", !dbg !136\n}"
    },
    "sys_open3": {
      "hash": "8e26451ac5bf2d7a",
      "sig_hash": "5b5345180d41c978",
      "ir": "define i32 @\"sys_open3\"(i8* %\"path.arg\", i32 %\"flags.arg\", i32 %\"mode.arg\") alignstack(16) !dbg !30\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !137, metadata !7), !dbg !138\n  %\"flags\" = alloca i32\n  store i32 %\"flags.arg\", i32* %\"flags\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"flags\", metadata !139, metadata !7), !dbg !138\n  %\"mode\" = alloca i32\n  store i32 %\"mode.arg\", i32* %\"mode\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"mode\", metadata !140, metadata !7), !dbg !138\n  %\".11\" = load i8*, i8** %\"path\", !dbg !141\n  %\".12\" = ptrtoint i8* %\".11\" to i64 , !dbg !141\n  %\".13\" = load i32, i32* %\"flags\", !dbg !141\n  %\".14\" = sext i32 %\".13\" to i64 , !dbg !141\n  %\".15\" = load i32, i32* %\"mode\", !dbg !141\n  %\".16\" = sext i32 %\".15\" to i64 , !dbg !141\n  %\".17\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 2, i64 %\".12\", i64 %\".14\", i64 %\".16\"), !dbg !141\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !141\n  ret i32 %\".18\", !dbg !141\n}"
    },
    "sys_close": {
      "hash": "8a263a8d9d509709",
      "sig_hash": "c8d1fe2642aeac35",
      "ir": "define i32 @\"sys_close\"(i32 %\"fd.arg\") alignstack(16) !dbg !31\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !142, metadata !7), !dbg !143\n  %\".5\" = load i32, i32* %\"fd\", !dbg !144\n  %\".6\" = sext i32 %\".5\" to i64 , !dbg !144\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 3, i64 %\".6\"), !dbg !144\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !144\n  ret i32 %\".8\", !dbg !144\n}"
    },
    "sys_lseek": {
      "hash": "76a0da52d5b87bb3",
      "sig_hash": "472b58567b35c85a",
      "ir": "define i64 @\"sys_lseek\"(i32 %\"fd.arg\", i64 %\"offset.arg\", i32 %\"whence.arg\") alignstack(16) !dbg !32\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !145, metadata !7), !dbg !146\n  %\"offset\" = alloca i64\n  store i64 %\"offset.arg\", i64* %\"offset\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"offset\", metadata !147, metadata !7), !dbg !146\n  %\"whence\" = alloca i32\n  store i32 %\"whence.arg\", i32* %\"whence\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"whence\", metadata !148, metadata !7), !dbg !146\n  %\".11\" = load i32, i32* %\"fd\", !dbg !149\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !149\n  %\".13\" = load i64, i64* %\"offset\", !dbg !149\n  %\".14\" = load i32, i32* %\"whence\", !dbg !149\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !149\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 8, i64 %\".12\", i64 %\".13\", i64 %\".15\"), !dbg !149\n  ret i64 %\".16\", !dbg !149\n}"
    },
    "sys_ftruncate": {
      "hash": "147864c0e53afe74",
      "sig_hash": "baf14cbb129be35b",
      "ir": "define i32 @\"sys_ftruncate\"(i32 %\"fd.arg\", i64 %\"length.arg\") alignstack(16) !dbg !33\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !150, metadata !7), !dbg !151\n  %\"length\" = alloca i64\n  store i64 %\"length.arg\", i64* %\"length\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"length\", metadata !152, metadata !7), !dbg !151\n  %\".8\" = load i32, i32* %\"fd\", !dbg !153\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !153\n  %\".10\" = load i64, i64* %\"length\", !dbg !153\n  %\".11\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 77, i64 %\".9\", i64 %\".10\"), !dbg !153\n  %\".12\" = trunc i64 %\".11\" to i32 , !dbg !153\n  ret i32 %\".12\", !dbg !153\n}"
    },
    "sys_stat": {
      "hash": "4f2de9e28b7166c0",
      "sig_hash": "829dfeb465e05618",
      "ir": "define i32 @\"sys_stat\"(i8* %\"path.arg\", i8* %\"statbuf.arg\") alignstack(16) !dbg !34\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !154, metadata !7), !dbg !155\n  %\"statbuf\" = alloca i8*\n  store i8* %\"statbuf.arg\", i8** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"statbuf\", metadata !156, metadata !7), !dbg !155\n  %\".8\" = load i8*, i8** %\"path\", !dbg !157\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !157\n  %\".10\" = load i8*, i8** %\"statbuf\", !dbg !157\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !157\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 4, i64 %\".9\", i64 %\".11\"), !dbg !157\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !157\n  ret i32 %\".13\", !dbg !157\n}"
    },
    "sys_fstat": {
      "hash": "1662c4cf52576731",
      "sig_hash": "43c8fba77801f9ef",
      "ir": "define i32 @\"sys_fstat\"(i32 %\"fd.arg\", i8* %\"statbuf.arg\") alignstack(16) !dbg !35\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !158, metadata !7), !dbg !159\n  %\"statbuf\" = alloca i8*\n  store i8* %\"statbuf.arg\", i8** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"statbuf\", metadata !160, metadata !7), !dbg !159\n  %\".8\" = load i32, i32* %\"fd\", !dbg !161\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !161\n  %\".10\" = load i8*, i8** %\"statbuf\", !dbg !161\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !161\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 5, i64 %\".9\", i64 %\".11\"), !dbg !161\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !161\n  ret i32 %\".13\", !dbg !161\n}"
    },
    "sys_lstat": {
      "hash": "947ace780c4bb637",
      "sig_hash": "59f5b3b8d88592e2",
      "ir": "define i32 @\"sys_lstat\"(i8* %\"path.arg\", i8* %\"statbuf.arg\") alignstack(16) !dbg !36\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !162, metadata !7), !dbg !163\n  %\"statbuf\" = alloca i8*\n  store i8* %\"statbuf.arg\", i8** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"statbuf\", metadata !164, metadata !7), !dbg !163\n  %\".8\" = load i8*, i8** %\"path\", !dbg !165\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !165\n  %\".10\" = load i8*, i8** %\"statbuf\", !dbg !165\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !165\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 6, i64 %\".9\", i64 %\".11\"), !dbg !165\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !165\n  ret i32 %\".13\", !dbg !165\n}"
    },
    "sys_chmod": {
      "hash": "1ae9ba456b44eb68",
      "sig_hash": "93bb206537238fee",
      "ir": "define i32 @\"sys_chmod\"(i8* %\"path.arg\", i32 %\"mode.arg\") alignstack(16) !dbg !37\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !166, metadata !7), !dbg !167\n  %\"mode\" = alloca i32\n  store i32 %\"mode.arg\", i32* %\"mode\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"mode\", metadata !168, metadata !7), !dbg !167\n  %\".8\" = load i8*, i8** %\"path\", !dbg !169\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !169\n  %\".10\" = load i32, i32* %\"mode\", !dbg !169\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !169\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 90, i64 %\".9\", i64 %\".11\"), !dbg !169\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !169\n  ret i32 %\".13\", !dbg !169\n}"
    },
    "sys_fchmod": {
      "hash": "43d2a33b9bcf5927",
      "sig_hash": "3a7d585f5708191d",
      "ir": "define i32 @\"sys_fchmod\"(i32 %\"fd.arg\", i32 %\"mode.arg\") alignstack(16) !dbg !38\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !170, metadata !7), !dbg !171\n  %\"mode\" = alloca i32\n  store i32 %\"mode.arg\", i32* %\"mode\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"mode\", metadata !172, metadata !7), !dbg !171\n  %\".8\" = load i32, i32* %\"fd\", !dbg !173\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !173\n  %\".10\" = load i32, i32* %\"mode\", !dbg !173\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !173\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 91, i64 %\".9\", i64 %\".11\"), !dbg !173\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !173\n  ret i32 %\".13\", !dbg !173\n}"
    },
    "sys_chown": {
      "hash": "34d6512953386045",
      "sig_hash": "65b9a68e6adf7984",
      "ir": "define i32 @\"sys_chown\"(i8* %\"path.arg\", i32 %\"uid.arg\", i32 %\"gid.arg\") alignstack(16) !dbg !39\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !174, metadata !7), !dbg !175\n  %\"uid\" = alloca i32\n  store i32 %\"uid.arg\", i32* %\"uid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"uid\", metadata !176, metadata !7), !dbg !175\n  %\"gid\" = alloca i32\n  store i32 %\"gid.arg\", i32* %\"gid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"gid\", metadata !177, metadata !7), !dbg !175\n  %\".11\" = load i8*, i8** %\"path\", !dbg !178\n  %\".12\" = ptrtoint i8* %\".11\" to i64 , !dbg !178\n  %\".13\" = load i32, i32* %\"uid\", !dbg !178\n  %\".14\" = sext i32 %\".13\" to i64 , !dbg !178\n  %\".15\" = load i32, i32* %\"gid\", !dbg !178\n  %\".16\" = sext i32 %\".15\" to i64 , !dbg !178\n  %\".17\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 92, i64 %\".12\", i64 %\".14\", i64 %\".16\"), !dbg !178\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !178\n  ret i32 %\".18\", !dbg !178\n}"
    },
    "sys_fchown": {
      "hash": "44667f6a2a988b2e",
      "sig_hash": "eed19da73481331f",
      "ir": "define i32 @\"sys_fchown\"(i32 %\"fd.arg\", i32 %\"uid.arg\", i32 %\"gid.arg\") alignstack(16) !dbg !40\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !179, metadata !7), !dbg !180\n  %\"uid\" = alloca i32\n  store i32 %\"uid.arg\", i32* %\"uid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"uid\", metadata !181, metadata !7), !dbg !180\n  %\"gid\" = alloca i32\n  store i32 %\"gid.arg\", i32* %\"gid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"gid\", metadata !182, metadata !7), !dbg !180\n  %\".11\" = load i32, i32* %\"fd\", !dbg !183\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !183\n  %\".13\" = load i32, i32* %\"uid\", !dbg !183\n  %\".14\" = sext i32 %\".13\" to i64 , !dbg !183\n  %\".15\" = load i32, i32* %\"gid\", !dbg !183\n  %\".16\" = sext i32 %\".15\" to i64 , !dbg !183\n  %\".17\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 93, i64 %\".12\", i64 %\".14\", i64 %\".16\"), !dbg !183\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !183\n  ret i32 %\".18\", !dbg !183\n}"
    },
    "sys_access": {
      "hash": "1fc21af668ddf531",
      "sig_hash": "6e3a1c8ff91b3fca",
      "ir": "define i32 @\"sys_access\"(i8* %\"path.arg\", i32 %\"mode.arg\") alignstack(16) !dbg !41\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !184, metadata !7), !dbg !185\n  %\"mode\" = alloca i32\n  store i32 %\"mode.arg\", i32* %\"mode\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"mode\", metadata !186, metadata !7), !dbg !185\n  %\".8\" = load i8*, i8** %\"path\", !dbg !187\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !187\n  %\".10\" = load i32, i32* %\"mode\", !dbg !187\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !187\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 21, i64 %\".9\", i64 %\".11\"), !dbg !187\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !187\n  ret i32 %\".13\", !dbg !187\n}"
    },
    "sys_utimensat": {
      "hash": "ce8f371b3c38e63f",
      "sig_hash": "6cdcca3ef20cdd40",
      "ir": "define i32 @\"sys_utimensat\"(i32 %\"dirfd.arg\", i8* %\"path.arg\", i64* %\"times.arg\", i32 %\"flags.arg\") alignstack(16) !dbg !42\n{\nentry:\n  %\"dirfd\" = alloca i32\n  store i32 %\"dirfd.arg\", i32* %\"dirfd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"dirfd\", metadata !188, metadata !7), !dbg !189\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !190, metadata !7), !dbg !189\n  %\"times\" = alloca i64*\n  store i64* %\"times.arg\", i64** %\"times\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"times\", metadata !192, metadata !7), !dbg !189\n  %\"flags\" = alloca i32\n  store i32 %\"flags.arg\", i32* %\"flags\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"flags\", metadata !193, metadata !7), !dbg !189\n  %\".14\" = load i32, i32* %\"dirfd\", !dbg !194\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !194\n  %\".16\" = load i8*, i8** %\"path\", !dbg !194\n  %\".17\" = ptrtoint i8* %\".16\" to i64 , !dbg !194\n  %\".18\" = load i64*, i64** %\"times\", !dbg !194\n  %\".19\" = ptrtoint i64* %\".18\" to i64 , !dbg !194\n  %\".20\" = load i32, i32* %\"flags\", !dbg !194\n  %\".21\" = sext i32 %\".20\" to i64 , !dbg !194\n  %\".22\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}\"(i64 280, i64 %\".15\", i64 %\".17\", i64 %\".19\", i64 %\".21\"), !dbg !194\n  %\".23\" = trunc i64 %\".22\" to i32 , !dbg !194\n  ret i32 %\".23\", !dbg !194\n}"
    },
    "sys_mkdir": {
      "hash": "2172aed8782c1707",
      "sig_hash": "ac3106ae10de1486",
      "ir": "define i32 @\"sys_mkdir\"(i8* %\"path.arg\", i32 %\"mode.arg\") alignstack(16) !dbg !43\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !195, metadata !7), !dbg !196\n  %\"mode\" = alloca i32\n  store i32 %\"mode.arg\", i32* %\"mode\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"mode\", metadata !197, metadata !7), !dbg !196\n  %\".8\" = load i8*, i8** %\"path\", !dbg !198\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !198\n  %\".10\" = load i32, i32* %\"mode\", !dbg !198\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !198\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 83, i64 %\".9\", i64 %\".11\"), !dbg !198\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !198\n  ret i32 %\".13\", !dbg !198\n}"
    },
    "sys_rmdir": {
      "hash": "3a1aa73e219cf7b3",
      "sig_hash": "e2d498ba149422f0",
      "ir": "define i32 @\"sys_rmdir\"(i8* %\"path.arg\") alignstack(16) !dbg !44\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !199, metadata !7), !dbg !200\n  %\".5\" = load i8*, i8** %\"path\", !dbg !201\n  %\".6\" = ptrtoint i8* %\".5\" to i64 , !dbg !201\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 84, i64 %\".6\"), !dbg !201\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !201\n  ret i32 %\".8\", !dbg !201\n}"
    },
    "sys_getdents64": {
      "hash": "3cd8f1e44df29a63",
      "sig_hash": "f3f8ae1b4ba30a99",
      "ir": "define i64 @\"sys_getdents64\"(i32 %\"fd.arg\", i8* %\"dirp.arg\", i64 %\"count.arg\") alignstack(16) !dbg !45\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !202, metadata !7), !dbg !203\n  %\"dirp\" = alloca i8*\n  store i8* %\"dirp.arg\", i8** %\"dirp\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"dirp\", metadata !204, metadata !7), !dbg !203\n  %\"count\" = alloca i64\n  store i64 %\"count.arg\", i64* %\"count\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"count\", metadata !205, metadata !7), !dbg !203\n  %\".11\" = load i32, i32* %\"fd\", !dbg !206\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !206\n  %\".13\" = load i8*, i8** %\"dirp\", !dbg !206\n  %\".14\" = ptrtoint i8* %\".13\" to i64 , !dbg !206\n  %\".15\" = load i64, i64* %\"count\", !dbg !206\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 217, i64 %\".12\", i64 %\".14\", i64 %\".15\"), !dbg !206\n  ret i64 %\".16\", !dbg !206\n}"
    },
    "sys_unlink": {
      "hash": "5f064d1db87bdb8d",
      "sig_hash": "e9863b109a08a85e",
      "ir": "define i32 @\"sys_unlink\"(i8* %\"path.arg\") alignstack(16) !dbg !46\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !207, metadata !7), !dbg !208\n  %\".5\" = load i8*, i8** %\"path\", !dbg !209\n  %\".6\" = ptrtoint i8* %\".5\" to i64 , !dbg !209\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 87, i64 %\".6\"), !dbg !209\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !209\n  ret i32 %\".8\", !dbg !209\n}"
    },
    "sys_rename": {
      "hash": "3b7f12bf3543061c",
      "sig_hash": "b93b418aa117255f",
      "ir": "define i32 @\"sys_rename\"(i8* %\"oldpath.arg\", i8* %\"newpath.arg\") alignstack(16) !dbg !47\n{\nentry:\n  %\"oldpath\" = alloca i8*\n  store i8* %\"oldpath.arg\", i8** %\"oldpath\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"oldpath\", metadata !210, metadata !7), !dbg !211\n  %\"newpath\" = alloca i8*\n  store i8* %\"newpath.arg\", i8** %\"newpath\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"newpath\", metadata !212, metadata !7), !dbg !211\n  %\".8\" = load i8*, i8** %\"oldpath\", !dbg !213\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !213\n  %\".10\" = load i8*, i8** %\"newpath\", !dbg !213\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !213\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 82, i64 %\".9\", i64 %\".11\"), !dbg !213\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !213\n  ret i32 %\".13\", !dbg !213\n}"
    },
    "sys_link": {
      "hash": "6cc3c698029d0ead",
      "sig_hash": "cef026210656bfe6",
      "ir": "define i32 @\"sys_link\"(i8* %\"oldpath.arg\", i8* %\"newpath.arg\") alignstack(16) !dbg !48\n{\nentry:\n  %\"oldpath\" = alloca i8*\n  store i8* %\"oldpath.arg\", i8** %\"oldpath\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"oldpath\", metadata !214, metadata !7), !dbg !215\n  %\"newpath\" = alloca i8*\n  store i8* %\"newpath.arg\", i8** %\"newpath\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"newpath\", metadata !216, metadata !7), !dbg !215\n  %\".8\" = load i8*, i8** %\"oldpath\", !dbg !217\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !217\n  %\".10\" = load i8*, i8** %\"newpath\", !dbg !217\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !217\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 86, i64 %\".9\", i64 %\".11\"), !dbg !217\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !217\n  ret i32 %\".13\", !dbg !217\n}"
    },
    "sys_symlink": {
      "hash": "0c9fd699ac47241f",
      "sig_hash": "dd2145d4a0227ac9",
      "ir": "define i32 @\"sys_symlink\"(i8* %\"target.arg\", i8* %\"linkpath.arg\") alignstack(16) !dbg !49\n{\nentry:\n  %\"target\" = alloca i8*\n  store i8* %\"target.arg\", i8** %\"target\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"target\", metadata !218, metadata !7), !dbg !219\n  %\"linkpath\" = alloca i8*\n  store i8* %\"linkpath.arg\", i8** %\"linkpath\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"linkpath\", metadata !220, metadata !7), !dbg !219\n  %\".8\" = load i8*, i8** %\"target\", !dbg !221\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !221\n  %\".10\" = load i8*, i8** %\"linkpath\", !dbg !221\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !221\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 88, i64 %\".9\", i64 %\".11\"), !dbg !221\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !221\n  ret i32 %\".13\", !dbg !221\n}"
    },
    "sys_readlink": {
      "hash": "b4cf4594d4ab65f7",
      "sig_hash": "eea28c6bfe0b681e",
      "ir": "define i64 @\"sys_readlink\"(i8* %\"path.arg\", i8* %\"buf.arg\", i64 %\"size.arg\") alignstack(16) !dbg !50\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !222, metadata !7), !dbg !223\n  %\"buf\" = alloca i8*\n  store i8* %\"buf.arg\", i8** %\"buf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"buf\", metadata !224, metadata !7), !dbg !223\n  %\"size\" = alloca i64\n  store i64 %\"size.arg\", i64* %\"size\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"size\", metadata !225, metadata !7), !dbg !223\n  %\".11\" = load i8*, i8** %\"path\", !dbg !226\n  %\".12\" = ptrtoint i8* %\".11\" to i64 , !dbg !226\n  %\".13\" = load i8*, i8** %\"buf\", !dbg !226\n  %\".14\" = ptrtoint i8* %\".13\" to i64 , !dbg !226\n  %\".15\" = load i64, i64* %\"size\", !dbg !226\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 89, i64 %\".12\", i64 %\".14\", i64 %\".15\"), !dbg !226\n  ret i64 %\".16\", !dbg !226\n}"
    },
    "sys_mprotect": {
      "hash": "2ba54e46ca85b9eb",
      "sig_hash": "3ee5f023b802740d",
      "ir": "define i32 @\"sys_mprotect\"(i8* %\"addr.arg\", i64 %\"length.arg\", i32 %\"prot.arg\") alignstack(16) !dbg !51\n{\nentry:\n  %\"addr\" = alloca i8*\n  store i8* %\"addr.arg\", i8** %\"addr\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"addr\", metadata !227, metadata !7), !dbg !228\n  %\"length\" = alloca i64\n  store i64 %\"length.arg\", i64* %\"length\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"length\", metadata !229, metadata !7), !dbg !228\n  %\"prot\" = alloca i32\n  store i32 %\"prot.arg\", i32* %\"prot\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"prot\", metadata !230, metadata !7), !dbg !228\n  %\".11\" = load i8*, i8** %\"addr\", !dbg !231\n  %\".12\" = ptrtoint i8* %\".11\" to i64 , !dbg !231\n  %\".13\" = load i64, i64* %\"length\", !dbg !231\n  %\".14\" = load i32, i32* %\"prot\", !dbg !231\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !231\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 10, i64 %\".12\", i64 %\".13\", i64 %\".15\"), !dbg !231\n  %\".17\" = trunc i64 %\".16\" to i32 , !dbg !231\n  ret i32 %\".17\", !dbg !231\n}"
    },
    "sys_exit": {
      "hash": "ea132443dd3d3545",
      "sig_hash": "4b090e7a69bb3a53",
      "ir": "define i32 @\"sys_exit\"(i32 %\"status.arg\") alignstack(16) !dbg !52\n{\nentry:\n  %\"status\" = alloca i32\n  store i32 %\"status.arg\", i32* %\"status\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"status\", metadata !232, metadata !7), !dbg !233\n  %\".5\" = load i32, i32* %\"status\", !dbg !234\n  %\".6\" = sext i32 %\".5\" to i64 , !dbg !234\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 %\".6\"), !dbg !234\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !234\n  ret i32 %\".8\", !dbg !234\n}"
    },
    "sys_getppid": {
      "hash": "c29f455fca126d0d",
      "sig_hash": "993f15e8abf35fb0",
      "ir": "define i32 @\"sys_getppid\"() alignstack(16) !dbg !53\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 110), !dbg !235\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !235\n  ret i32 %\".3\", !dbg !235\n}"
    },
    "sys_getuid": {
      "hash": "f46c814276ac9893",
      "sig_hash": "74ba2c9d706fa445",
      "ir": "define i32 @\"sys_getuid\"() alignstack(16) !dbg !54\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 102), !dbg !236\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !236\n  ret i32 %\".3\", !dbg !236\n}"
    },
    "sys_getgid": {
      "hash": "68755c3aee34b9ff",
      "sig_hash": "2a1d171440ca38e0",
      "ir": "define i32 @\"sys_getgid\"() alignstack(16) !dbg !55\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 104), !dbg !237\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !237\n  ret i32 %\".3\", !dbg !237\n}"
    },
    "sys_geteuid": {
      "hash": "65d99d8c5e8e7233",
      "sig_hash": "65ec6a09487d0b40",
      "ir": "define i32 @\"sys_geteuid\"() alignstack(16) !dbg !56\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 107), !dbg !238\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !238\n  ret i32 %\".3\", !dbg !238\n}"
    },
    "sys_getegid": {
      "hash": "9fcb31b30816e7b5",
      "sig_hash": "67e120e78d36b39b",
      "ir": "define i32 @\"sys_getegid\"() alignstack(16) !dbg !57\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 108), !dbg !239\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !239\n  ret i32 %\".3\", !dbg !239\n}"
    },
    "sys_fork": {
      "hash": "5744252236558154",
      "sig_hash": "1aa4781261614ee5",
      "ir": "define i32 @\"sys_fork\"() alignstack(16) !dbg !58\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 57), !dbg !240\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !240\n  ret i32 %\".3\", !dbg !240\n}"
    },
    "sys_execve": {
      "hash": "25717ece427ab1b1",
      "sig_hash": "6004b2bc3a162828",
      "ir": "define i32 @\"sys_execve\"(i8* %\"path.arg\", i8** %\"argv.arg\", i8** %\"envp.arg\") alignstack(16) !dbg !59\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !241, metadata !7), !dbg !242\n  %\"argv\" = alloca i8**\n  store i8** %\"argv.arg\", i8*** %\"argv\"\n  call void @\"llvm.dbg.declare\"(metadata i8*** %\"argv\", metadata !244, metadata !7), !dbg !242\n  %\"envp\" = alloca i8**\n  store i8** %\"envp.arg\", i8*** %\"envp\"\n  call void @\"llvm.dbg.declare\"(metadata i8*** %\"envp\", metadata !245, metadata !7), !dbg !242\n  %\".11\" = load i8*, i8** %\"path\", !dbg !246\n  %\".12\" = ptrtoint i8* %\".11\" to i64 , !dbg !246\n  %\".13\" = load i8**, i8*** %\"argv\", !dbg !246\n  %\".14\" = ptrtoint i8** %\".13\" to i64 , !dbg !246\n  %\".15\" = load i8**, i8*** %\"envp\", !dbg !246\n  %\".16\" = ptrtoint i8** %\".15\" to i64 , !dbg !246\n  %\".17\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 59, i64 %\".12\", i64 %\".14\", i64 %\".16\"), !dbg !246\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !246\n  ret i32 %\".18\", !dbg !246\n}"
    },
    "sys_wait4": {
      "hash": "b1efd4c98a118844",
      "sig_hash": "34eadac1f69c9f25",
      "ir": "define i32 @\"sys_wait4\"(i32 %\"pid.arg\", i32* %\"status.arg\", i32 %\"options.arg\", i8* %\"rusage.arg\") alignstack(16) !dbg !60\n{\nentry:\n  %\"pid\" = alloca i32\n  store i32 %\"pid.arg\", i32* %\"pid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"pid\", metadata !247, metadata !7), !dbg !248\n  %\"status\" = alloca i32*\n  store i32* %\"status.arg\", i32** %\"status\"\n  call void @\"llvm.dbg.declare\"(metadata i32** %\"status\", metadata !249, metadata !7), !dbg !248\n  %\"options\" = alloca i32\n  store i32 %\"options.arg\", i32* %\"options\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"options\", metadata !250, metadata !7), !dbg !248\n  %\"rusage\" = alloca i8*\n  store i8* %\"rusage.arg\", i8** %\"rusage\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"rusage\", metadata !251, metadata !7), !dbg !248\n  %\".14\" = load i32, i32* %\"pid\", !dbg !252\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !252\n  %\".16\" = load i32*, i32** %\"status\", !dbg !252\n  %\".17\" = ptrtoint i32* %\".16\" to i64 , !dbg !252\n  %\".18\" = load i32, i32* %\"options\", !dbg !252\n  %\".19\" = sext i32 %\".18\" to i64 , !dbg !252\n  %\".20\" = load i8*, i8** %\"rusage\", !dbg !252\n  %\".21\" = ptrtoint i8* %\".20\" to i64 , !dbg !252\n  %\".22\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}\"(i64 61, i64 %\".15\", i64 %\".17\", i64 %\".19\", i64 %\".21\"), !dbg !252\n  %\".23\" = trunc i64 %\".22\" to i32 , !dbg !252\n  ret i32 %\".23\", !dbg !252\n}"
    },
    "sys_kill": {
      "hash": "bd32fad66ddb4640",
      "sig_hash": "d206d63f833f9e42",
      "ir": "define i32 @\"sys_kill\"(i32 %\"pid.arg\", i32 %\"sig.arg\") alignstack(16) !dbg !61\n{\nentry:\n  %\"pid\" = alloca i32\n  store i32 %\"pid.arg\", i32* %\"pid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"pid\", metadata !253, metadata !7), !dbg !254\n  %\"sig\" = alloca i32\n  store i32 %\"sig.arg\", i32* %\"sig\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"sig\", metadata !255, metadata !7), !dbg !254\n  %\".8\" = load i32, i32* %\"pid\", !dbg !256\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !256\n  %\".10\" = load i32, i32* %\"sig\", !dbg !256\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !256\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 62, i64 %\".9\", i64 %\".11\"), !dbg !256\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !256\n  ret i32 %\".13\", !dbg !256\n}"
    },
    "sys_dup": {
      "hash": "d7d9c6229ff51202",
      "sig_hash": "421c6dff4dff87d5",
      "ir": "define i32 @\"sys_dup\"(i32 %\"oldfd.arg\") alignstack(16) !dbg !62\n{\nentry:\n  %\"oldfd\" = alloca i32\n  store i32 %\"oldfd.arg\", i32* %\"oldfd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"oldfd\", metadata !257, metadata !7), !dbg !258\n  %\".5\" = load i32, i32* %\"oldfd\", !dbg !259\n  %\".6\" = sext i32 %\".5\" to i64 , !dbg !259\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 32, i64 %\".6\"), !dbg !259\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !259\n  ret i32 %\".8\", !dbg !259\n}"
    },
    "sys_dup2": {
      "hash": "b676ed3e376f1689",
      "sig_hash": "290cacad8d37250e",
      "ir": "define i32 @\"sys_dup2\"(i32 %\"oldfd.arg\", i32 %\"newfd.arg\") alignstack(16) !dbg !63\n{\nentry:\n  %\"oldfd\" = alloca i32\n  store i32 %\"oldfd.arg\", i32* %\"oldfd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"oldfd\", metadata !260, metadata !7), !dbg !261\n  %\"newfd\" = alloca i32\n  store i32 %\"newfd.arg\", i32* %\"newfd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"newfd\", metadata !262, metadata !7), !dbg !261\n  %\".8\" = load i32, i32* %\"oldfd\", !dbg !263\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !263\n  %\".10\" = load i32, i32* %\"newfd\", !dbg !263\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !263\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 33, i64 %\".9\", i64 %\".11\"), !dbg !263\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !263\n  ret i32 %\".13\", !dbg !263\n}"
    },
    "sys_rt_sigaction": {
      "hash": "518504c3bea5142a",
      "sig_hash": "80c05f5fca7d7dd0",
      "ir": "define i32 @\"sys_rt_sigaction\"(i32 %\"signum.arg\", i8* %\"act.arg\", i8* %\"oldact.arg\", i64 %\"sigsetsize.arg\") alignstack(16) !dbg !64\n{\nentry:\n  %\"signum\" = alloca i32\n  store i32 %\"signum.arg\", i32* %\"signum\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"signum\", metadata !264, metadata !7), !dbg !265\n  %\"act\" = alloca i8*\n  store i8* %\"act.arg\", i8** %\"act\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"act\", metadata !266, metadata !7), !dbg !265\n  %\"oldact\" = alloca i8*\n  store i8* %\"oldact.arg\", i8** %\"oldact\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"oldact\", metadata !267, metadata !7), !dbg !265\n  %\"sigsetsize\" = alloca i64\n  store i64 %\"sigsetsize.arg\", i64* %\"sigsetsize\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"sigsetsize\", metadata !268, metadata !7), !dbg !265\n  %\".14\" = load i32, i32* %\"signum\", !dbg !269\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !269\n  %\".16\" = load i8*, i8** %\"act\", !dbg !269\n  %\".17\" = ptrtoint i8* %\".16\" to i64 , !dbg !269\n  %\".18\" = load i8*, i8** %\"oldact\", !dbg !269\n  %\".19\" = ptrtoint i8* %\".18\" to i64 , !dbg !269\n  %\".20\" = load i64, i64* %\"sigsetsize\", !dbg !269\n  %\".21\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}\"(i64 13, i64 %\".15\", i64 %\".17\", i64 %\".19\", i64 %\".20\"), !dbg !269\n  %\".22\" = trunc i64 %\".21\" to i32 , !dbg !269\n  ret i32 %\".22\", !dbg !269\n}"
    },
    "signal_ignore": {
      "hash": "fc73f821052b8c77",
      "sig_hash": "c5e55c035d256536",
      "ir": "define i32 @\"signal_ignore\"(i32 %\"signum.arg\") alignstack(16) !dbg !65\n{\nentry:\n  %\"signum\" = alloca i32\n  %\"act.addr\" = alloca [32 x i8], !dbg !272\n  %\"i.addr\" = alloca i64, !dbg !278\n  store i32 %\"signum.arg\", i32* %\"signum\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"signum\", metadata !270, metadata !7), !dbg !271\n  call void @\"llvm.dbg.declare\"(metadata [32 x i8]* %\"act.addr\", metadata !276, metadata !7), !dbg !277\n  store i64 0, i64* %\"i.addr\", !dbg !278\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"i.addr\", metadata !279, metadata !7), !dbg !280\n  br label %\"while.cond\", !dbg !281\nwhile.cond:\n  %\".9\" = load i64, i64* %\"i.addr\", !dbg !281\n  %\".10\" = icmp slt i64 %\".9\", 32 , !dbg !281\n  br i1 %\".10\", label %\"while.body\", label %\"while.end\", !dbg !281\nwhile.body:\n  %\".12\" = load i64, i64* %\"i.addr\", !dbg !282\n  %\".13\" = getelementptr [32 x i8], [32 x i8]* %\"act.addr\", i32 0, i64 %\".12\" , !dbg !282\n  %\".14\" = trunc i64 0 to i8 , !dbg !282\n  store i8 %\".14\", i8* %\".13\", !dbg !282\n  %\".16\" = load i64, i64* %\"i.addr\", !dbg !283\n  %\".17\" = add i64 %\".16\", 1, !dbg !283\n  store i64 %\".17\", i64* %\"i.addr\", !dbg !283\n  br label %\"while.cond\", !dbg !283\nwhile.end:\n  %\".20\" = getelementptr [32 x i8], [32 x i8]* %\"act.addr\", i32 0, i64 0 , !dbg !284\n  %\".21\" = trunc i64 1 to i8 , !dbg !284\n  store i8 %\".21\", i8* %\".20\", !dbg !284\n  %\".23\" = load i32, i32* %\"signum\", !dbg !285\n  %\".24\" = getelementptr [32 x i8], [32 x i8]* %\"act.addr\", i32 0, i64 0 , !dbg !285\n  %\".25\" = call i32 @\"sys_rt_sigaction\"(i32 %\".23\", i8* %\".24\", i8* null, i64 8), !dbg !285\n  ret i32 %\".25\", !dbg !285\n}"
    },
    "shutdown_requested": {
      "hash": "2ab5e17994f3902e",
      "sig_hash": "42450cbf9e056738",
      "ir": "define i32 @\"shutdown_requested\"() alignstack(16) !dbg !66\n{\nentry:\n  %\".2\" = load i32, i32* @\"g_shutdown_requested\", !dbg !286\n  ret i32 %\".2\", !dbg !286\n}"
    },
    "request_shutdown": {
      "hash": "65420e6f652eeb60",
      "sig_hash": "ceffd5f71d500265",
      "ir": "define i32 @\"request_shutdown\"() alignstack(16) !dbg !67\n{\nentry:\n  %\".2\" = trunc i64 1 to i32 , !dbg !287\n  store i32 %\".2\", i32* @\"g_shutdown_requested\", !dbg !287\n  ret i32 0, !dbg !287\n}"
    },
    "reset_shutdown": {
      "hash": "fc07d4f3da761d38",
      "sig_hash": "1ec169b3180e2598",
      "ir": "define i32 @\"reset_shutdown\"() alignstack(16) !dbg !68\n{\nentry:\n  %\".2\" = trunc i64 0 to i32 , !dbg !288\n  store i32 %\".2\", i32* @\"g_shutdown_requested\", !dbg !288\n  ret i32 0, !dbg !288\n}"
    },
    "sys_rt_sigprocmask": {
      "hash": "1da6ca53d908e3fd",
      "sig_hash": "b1d13f05cd285449",
      "ir": "define i32 @\"sys_rt_sigprocmask\"(i32 %\"how.arg\", i64* %\"set.arg\", i64* %\"oldset.arg\", i64 %\"sigsetsize.arg\") alignstack(16) !dbg !69\n{\nentry:\n  %\"how\" = alloca i32\n  store i32 %\"how.arg\", i32* %\"how\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"how\", metadata !289, metadata !7), !dbg !290\n  %\"set\" = alloca i64*\n  store i64* %\"set.arg\", i64** %\"set\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"set\", metadata !291, metadata !7), !dbg !290\n  %\"oldset\" = alloca i64*\n  store i64* %\"oldset.arg\", i64** %\"oldset\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"oldset\", metadata !292, metadata !7), !dbg !290\n  %\"sigsetsize\" = alloca i64\n  store i64 %\"sigsetsize.arg\", i64* %\"sigsetsize\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"sigsetsize\", metadata !293, metadata !7), !dbg !290\n  %\".14\" = load i32, i32* %\"how\", !dbg !294\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !294\n  %\".16\" = load i64*, i64** %\"set\", !dbg !294\n  %\".17\" = ptrtoint i64* %\".16\" to i64 , !dbg !294\n  %\".18\" = load i64*, i64** %\"oldset\", !dbg !294\n  %\".19\" = ptrtoint i64* %\".18\" to i64 , !dbg !294\n  %\".20\" = load i64, i64* %\"sigsetsize\", !dbg !294\n  %\".21\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}\"(i64 14, i64 %\".15\", i64 %\".17\", i64 %\".19\", i64 %\".20\"), !dbg !294\n  %\".22\" = trunc i64 %\".21\" to i32 , !dbg !294\n  ret i32 %\".22\", !dbg !294\n}"
    },
    "sys_signalfd4": {
      "hash": "2194fbda17133048",
      "sig_hash": "e3e4c7dd4a58d043",
      "ir": "define i32 @\"sys_signalfd4\"(i32 %\"fd.arg\", i64* %\"mask.arg\", i32 %\"flags.arg\") alignstack(16) !dbg !70\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !295, metadata !7), !dbg !296\n  %\"mask\" = alloca i64*\n  store i64* %\"mask.arg\", i64** %\"mask\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"mask\", metadata !297, metadata !7), !dbg !296\n  %\"flags\" = alloca i32\n  store i32 %\"flags.arg\", i32* %\"flags\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"flags\", metadata !298, metadata !7), !dbg !296\n  %\".11\" = load i32, i32* %\"fd\", !dbg !299\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !299\n  %\".13\" = load i64*, i64** %\"mask\", !dbg !299\n  %\".14\" = ptrtoint i64* %\".13\" to i64 , !dbg !299\n  %\".15\" = load i32, i32* %\"flags\", !dbg !299\n  %\".16\" = sext i32 %\".15\" to i64 , !dbg !299\n  %\".17\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}\"(i64 289, i64 %\".12\", i64 %\".14\", i64 8, i64 %\".16\"), !dbg !299\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !299\n  ret i32 %\".18\", !dbg !299\n}"
    },
    "signalfd_create_for_shutdown": {
      "hash": "8a15c08ee0662f57",
      "sig_hash": "7193a5d91921e20c",
      "ir": "define i32 @\"signalfd_create_for_shutdown\"() alignstack(16) !dbg !71\n{\nentry:\n  %\"mask.addr\" = alloca i64, !dbg !300\n  store i64 0, i64* %\"mask.addr\", !dbg !300\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"mask.addr\", metadata !301, metadata !7), !dbg !302\n  %\".4\" = load i64, i64* %\"mask.addr\", !dbg !303\n  %\".5\" = shl i64 1, 14, !dbg !303\n  %\".6\" = or i64 %\".4\", %\".5\", !dbg !303\n  store i64 %\".6\", i64* %\"mask.addr\", !dbg !303\n  %\".8\" = load i64, i64* %\"mask.addr\", !dbg !304\n  %\".9\" = shl i64 1, 1, !dbg !304\n  %\".10\" = or i64 %\".8\", %\".9\", !dbg !304\n  store i64 %\".10\", i64* %\"mask.addr\", !dbg !304\n  %\".12\" = bitcast i8* null to i64* , !dbg !305\n  %\".13\" = call i32 @\"sys_rt_sigprocmask\"(i32 0, i64* %\"mask.addr\", i64* %\".12\", i64 8), !dbg !305\n  %\".14\" = sext i32 %\".13\" to i64 , !dbg !306\n  %\".15\" = icmp slt i64 %\".14\", 0 , !dbg !306\n  br i1 %\".15\", label %\"if.then\", label %\"if.end\", !dbg !306\nif.then:\n  ret i32 %\".13\", !dbg !307\nif.end:\n  %\".18\" = sub i64 0, 1, !dbg !308\n  %\".19\" = trunc i64 %\".18\" to i32 , !dbg !308\n  %\".20\" = or i32 524288, 2048, !dbg !308\n  %\".21\" = call i32 @\"sys_signalfd4\"(i32 %\".19\", i64* %\"mask.addr\", i32 %\".20\"), !dbg !308\n  ret i32 %\".21\", !dbg !308\n}"
    },
    "signalfd_read": {
      "hash": "2bdd2538d6d41729",
      "sig_hash": "50dbea27815ee7f5",
      "ir": "define i32 @\"signalfd_read\"(i32 %\"fd.arg\") alignstack(16) !dbg !72\n{\nentry:\n  %\"fd\" = alloca i32\n  %\"result.addr\" = alloca i32, !dbg !315\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !309, metadata !7), !dbg !310\n  %\".5\" = or i32 1, 2, !dbg !311\n  %\".6\" = or i32 2, 32, !dbg !311\n  %\".7\" = sub i64 0, 1, !dbg !311\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !311\n  %\".9\" = call i8* @\"sys_mmap\"(i64 0, i64 4096, i32 %\".5\", i32 %\".6\", i32 %\".8\", i64 0), !dbg !311\n  %\".10\" = icmp eq i8* %\".9\", null , !dbg !312\n  br i1 %\".10\", label %\"or.merge\", label %\"or.right\", !dbg !312\nor.right:\n  %\".12\" = ptrtoint i8* %\".9\" to i64 , !dbg !312\n  %\".13\" = icmp slt i64 %\".12\", 0 , !dbg !312\n  br label %\"or.merge\", !dbg !312\nor.merge:\n  %\".15\" = phi  i1 [1, %\"entry\"], [%\".13\", %\"or.right\"] , !dbg !312\n  br i1 %\".15\", label %\"if.then\", label %\"if.end\", !dbg !312\nif.then:\n  %\".17\" = sub i64 0, 1, !dbg !313\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !313\n  ret i32 %\".18\", !dbg !313\nif.end:\n  %\".20\" = load i32, i32* %\"fd\", !dbg !314\n  %\".21\" = call i64 @\"sys_read\"(i32 %\".20\", i8* %\".9\", i64 128), !dbg !314\n  %\".22\" = trunc i64 0 to i32 , !dbg !315\n  store i32 %\".22\", i32* %\"result.addr\", !dbg !315\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"result.addr\", metadata !316, metadata !7), !dbg !317\n  %\".25\" = icmp slt i64 %\".21\", 0 , !dbg !318\n  br i1 %\".25\", label %\"if.then.1\", label %\"if.else\", !dbg !318\nif.then.1:\n  %\".27\" = sub i64 0, 11, !dbg !318\n  %\".28\" = icmp eq i64 %\".21\", %\".27\" , !dbg !318\n  br i1 %\".28\", label %\"if.then.2\", label %\"if.else.1\", !dbg !318\nif.else:\n  %\".36\" = icmp eq i64 %\".21\", 128 , !dbg !320\n  br i1 %\".36\", label %\"if.then.3\", label %\"if.end.3\", !dbg !320\nif.end.1:\n  %\".75\" = call i32 @\"sys_munmap\"(i8* %\".9\", i64 4096), !dbg !325\n  %\".76\" = load i32, i32* %\"result.addr\", !dbg !326\n  ret i32 %\".76\", !dbg !326\nif.then.2:\n  %\".30\" = trunc i64 0 to i32 , !dbg !319\n  store i32 %\".30\", i32* %\"result.addr\", !dbg !319\n  br label %\"if.end.2\", !dbg !320\nif.else.1:\n  %\".32\" = trunc i64 %\".21\" to i32 , !dbg !320\n  store i32 %\".32\", i32* %\"result.addr\", !dbg !320\n  br label %\"if.end.2\", !dbg !320\nif.end.2:\n  br label %\"if.end.1\", !dbg !324\nif.then.3:\n  %\".38\" = getelementptr i8, i8* %\".9\", i64 0 , !dbg !321\n  %\".39\" = load i8, i8* %\".38\", !dbg !321\n  %\".40\" = zext i8 %\".39\" to i32 , !dbg !321\n  store i32 %\".40\", i32* %\"result.addr\", !dbg !321\n  %\".42\" = load i32, i32* %\"result.addr\", !dbg !322\n  %\".43\" = getelementptr i8, i8* %\".9\", i64 1 , !dbg !322\n  %\".44\" = load i8, i8* %\".43\", !dbg !322\n  %\".45\" = zext i8 %\".44\" to i32 , !dbg !322\n  %\".46\" = sext i32 %\".45\" to i64 , !dbg !322\n  %\".47\" = shl i64 %\".46\", 8, !dbg !322\n  %\".48\" = sext i32 %\".42\" to i64 , !dbg !322\n  %\".49\" = add i64 %\".48\", %\".47\", !dbg !322\n  %\".50\" = trunc i64 %\".49\" to i32 , !dbg !322\n  store i32 %\".50\", i32* %\"result.addr\", !dbg !322\n  %\".52\" = load i32, i32* %\"result.addr\", !dbg !323\n  %\".53\" = getelementptr i8, i8* %\".9\", i64 2 , !dbg !323\n  %\".54\" = load i8, i8* %\".53\", !dbg !323\n  %\".55\" = zext i8 %\".54\" to i32 , !dbg !323\n  %\".56\" = sext i32 %\".55\" to i64 , !dbg !323\n  %\".57\" = shl i64 %\".56\", 16, !dbg !323\n  %\".58\" = sext i32 %\".52\" to i64 , !dbg !323\n  %\".59\" = add i64 %\".58\", %\".57\", !dbg !323\n  %\".60\" = trunc i64 %\".59\" to i32 , !dbg !323\n  store i32 %\".60\", i32* %\"result.addr\", !dbg !323\n  %\".62\" = load i32, i32* %\"result.addr\", !dbg !324\n  %\".63\" = getelementptr i8, i8* %\".9\", i64 3 , !dbg !324\n  %\".64\" = load i8, i8* %\".63\", !dbg !324\n  %\".65\" = zext i8 %\".64\" to i32 , !dbg !324\n  %\".66\" = sext i32 %\".65\" to i64 , !dbg !324\n  %\".67\" = shl i64 %\".66\", 24, !dbg !324\n  %\".68\" = sext i32 %\".62\" to i64 , !dbg !324\n  %\".69\" = add i64 %\".68\", %\".67\", !dbg !324\n  %\".70\" = trunc i64 %\".69\" to i32 , !dbg !324\n  store i32 %\".70\", i32* %\"result.addr\", !dbg !324\n  br label %\"if.end.3\", !dbg !324\nif.end.3:\n  br label %\"if.end.1\", !dbg !324\n}"
    },
    "sys_nanosleep": {
      "hash": "8287dec5d1ae28b7",
      "sig_hash": "40e5b42e197cc9d9",
      "ir": "define i32 @\"sys_nanosleep\"(i64* %\"req.arg\", i64* %\"rem.arg\") alignstack(16) !dbg !73\n{\nentry:\n  %\"req\" = alloca i64*\n  store i64* %\"req.arg\", i64** %\"req\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"req\", metadata !327, metadata !7), !dbg !328\n  %\"rem\" = alloca i64*\n  store i64* %\"rem.arg\", i64** %\"rem\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"rem\", metadata !329, metadata !7), !dbg !328\n  %\".8\" = load i64*, i64** %\"req\", !dbg !330\n  %\".9\" = ptrtoint i64* %\".8\" to i64 , !dbg !330\n  %\".10\" = load i64*, i64** %\"rem\", !dbg !330\n  %\".11\" = ptrtoint i64* %\".10\" to i64 , !dbg !330\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 35, i64 %\".9\", i64 %\".11\"), !dbg !330\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !330\n  ret i32 %\".13\", !dbg !330\n}"
    },
    "sys_gettimeofday": {
      "hash": "90d842b1c850fe42",
      "sig_hash": "001a747621899ff3",
      "ir": "define i32 @\"sys_gettimeofday\"(%\"struct.ritz_module_1.Timeval\"* %\"tv.arg\", i8* %\"tz.arg\") alignstack(16) !dbg !74\n{\nentry:\n  %\"tv\" = alloca %\"struct.ritz_module_1.Timeval\"*\n  store %\"struct.ritz_module_1.Timeval\"* %\"tv.arg\", %\"struct.ritz_module_1.Timeval\"** %\"tv\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Timeval\"** %\"tv\", metadata !333, metadata !7), !dbg !334\n  %\"tz\" = alloca i8*\n  store i8* %\"tz.arg\", i8** %\"tz\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"tz\", metadata !335, metadata !7), !dbg !334\n  %\".8\" = load %\"struct.ritz_module_1.Timeval\"*, %\"struct.ritz_module_1.Timeval\"** %\"tv\", !dbg !336\n  %\".9\" = ptrtoint %\"struct.ritz_module_1.Timeval\"* %\".8\" to i64 , !dbg !336\n  %\".10\" = load i8*, i8** %\"tz\", !dbg !336\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !336\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 96, i64 %\".9\", i64 %\".11\"), !dbg !336\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !336\n  ret i32 %\".13\", !dbg !336\n}"
    },
    "sys_poll": {
      "hash": "6f9c8042fca52ae2",
      "sig_hash": "adbf4b391bb4c86f",
      "ir": "define i32 @\"sys_poll\"(%\"struct.ritz_module_1.PollFd\"* %\"fds.arg\", i64 %\"nfds.arg\", i32 %\"timeout.arg\") alignstack(16) !dbg !75\n{\nentry:\n  %\"fds\" = alloca %\"struct.ritz_module_1.PollFd\"*\n  store %\"struct.ritz_module_1.PollFd\"* %\"fds.arg\", %\"struct.ritz_module_1.PollFd\"** %\"fds\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.PollFd\"** %\"fds\", metadata !339, metadata !7), !dbg !340\n  %\"nfds\" = alloca i64\n  store i64 %\"nfds.arg\", i64* %\"nfds\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"nfds\", metadata !341, metadata !7), !dbg !340\n  %\"timeout\" = alloca i32\n  store i32 %\"timeout.arg\", i32* %\"timeout\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"timeout\", metadata !342, metadata !7), !dbg !340\n  %\".11\" = load %\"struct.ritz_module_1.PollFd\"*, %\"struct.ritz_module_1.PollFd\"** %\"fds\", !dbg !343\n  %\".12\" = ptrtoint %\"struct.ritz_module_1.PollFd\"* %\".11\" to i64 , !dbg !343\n  %\".13\" = load i64, i64* %\"nfds\", !dbg !343\n  %\".14\" = load i32, i32* %\"timeout\", !dbg !343\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !343\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 7, i64 %\".12\", i64 %\".13\", i64 %\".15\"), !dbg !343\n  %\".17\" = trunc i64 %\".16\" to i32 , !dbg !343\n  ret i32 %\".17\", !dbg !343\n}"
    },
    "sys_sendfile": {
      "hash": "2bca060df7972e55",
      "sig_hash": "e50b86cdd568c50e",
      "ir": "define i64 @\"sys_sendfile\"(i32 %\"out_fd.arg\", i32 %\"in_fd.arg\", i64* %\"offset.arg\", i64 %\"count.arg\") alignstack(16) !dbg !76\n{\nentry:\n  %\"out_fd\" = alloca i32\n  store i32 %\"out_fd.arg\", i32* %\"out_fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"out_fd\", metadata !344, metadata !7), !dbg !345\n  %\"in_fd\" = alloca i32\n  store i32 %\"in_fd.arg\", i32* %\"in_fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"in_fd\", metadata !346, metadata !7), !dbg !345\n  %\"offset\" = alloca i64*\n  store i64* %\"offset.arg\", i64** %\"offset\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"offset\", metadata !347, metadata !7), !dbg !345\n  %\"count\" = alloca i64\n  store i64 %\"count.arg\", i64* %\"count\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"count\", metadata !348, metadata !7), !dbg !345\n  %\".14\" = load i32, i32* %\"out_fd\", !dbg !349\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !349\n  %\".16\" = load i32, i32* %\"in_fd\", !dbg !349\n  %\".17\" = sext i32 %\".16\" to i64 , !dbg !349\n  %\".18\" = load i64*, i64** %\"offset\", !dbg !349\n  %\".19\" = ptrtoint i64* %\".18\" to i64 , !dbg !349\n  %\".20\" = load i64, i64* %\"count\", !dbg !349\n  %\".21\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}\"(i64 40, i64 %\".15\", i64 %\".17\", i64 %\".19\", i64 %\".20\"), !dbg !349\n  ret i64 %\".21\", !dbg !349\n}"
    },
    "sys_ioctl": {
      "hash": "b50038aaf934e617",
      "sig_hash": "c372d89b75558910",
      "ir": "define i32 @\"sys_ioctl\"(i32 %\"fd.arg\", i64 %\"request.arg\", i8* %\"arg.arg\") alignstack(16) !dbg !77\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !350, metadata !7), !dbg !351\n  %\"request\" = alloca i64\n  store i64 %\"request.arg\", i64* %\"request\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"request\", metadata !352, metadata !7), !dbg !351\n  %\"arg\" = alloca i8*\n  store i8* %\"arg.arg\", i8** %\"arg\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"arg\", metadata !353, metadata !7), !dbg !351\n  %\".11\" = load i32, i32* %\"fd\", !dbg !354\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !354\n  %\".13\" = load i64, i64* %\"request\", !dbg !354\n  %\".14\" = load i8*, i8** %\"arg\", !dbg !354\n  %\".15\" = ptrtoint i8* %\".14\" to i64 , !dbg !354\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 16, i64 %\".12\", i64 %\".13\", i64 %\".15\"), !dbg !354\n  %\".17\" = trunc i64 %\".16\" to i32 , !dbg !354\n  ret i32 %\".17\", !dbg !354\n}"
    },
    "tcgetattr": {
      "hash": "a2e4f05479db1973",
      "sig_hash": "05438aa7217ae53a",
      "ir": "define i32 @\"tcgetattr\"(i32 %\"fd.arg\", %\"struct.ritz_module_1.Termios\"* %\"termios_p.arg\") alignstack(16) !dbg !78\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !355, metadata !7), !dbg !356\n  %\"termios_p\" = alloca %\"struct.ritz_module_1.Termios\"*\n  store %\"struct.ritz_module_1.Termios\"* %\"termios_p.arg\", %\"struct.ritz_module_1.Termios\"** %\"termios_p\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Termios\"** %\"termios_p\", metadata !359, metadata !7), !dbg !356\n  %\".8\" = load i32, i32* %\"fd\", !dbg !360\n  %\".9\" = load %\"struct.ritz_module_1.Termios\"*, %\"struct.ritz_module_1.Termios\"** %\"termios_p\", !dbg !360\n  %\".10\" = bitcast %\"struct.ritz_module_1.Termios\"* %\".9\" to i8* , !dbg !360\n  %\".11\" = call i32 @\"sys_ioctl\"(i32 %\".8\", i64 21505, i8* %\".10\"), !dbg !360\n  ret i32 %\".11\", !dbg !360\n}"
    },
    "tcsetattr": {
      "hash": "266df12aa5c289c5",
      "sig_hash": "d8030116811a15c0",
      "ir": "define i32 @\"tcsetattr\"(i32 %\"fd.arg\", %\"struct.ritz_module_1.Termios\"* %\"termios_p.arg\") alignstack(16) !dbg !79\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !361, metadata !7), !dbg !362\n  %\"termios_p\" = alloca %\"struct.ritz_module_1.Termios\"*\n  store %\"struct.ritz_module_1.Termios\"* %\"termios_p.arg\", %\"struct.ritz_module_1.Termios\"** %\"termios_p\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Termios\"** %\"termios_p\", metadata !363, metadata !7), !dbg !362\n  %\".8\" = load i32, i32* %\"fd\", !dbg !364\n  %\".9\" = load %\"struct.ritz_module_1.Termios\"*, %\"struct.ritz_module_1.Termios\"** %\"termios_p\", !dbg !364\n  %\".10\" = bitcast %\"struct.ritz_module_1.Termios\"* %\".9\" to i8* , !dbg !364\n  %\".11\" = call i32 @\"sys_ioctl\"(i32 %\".8\", i64 21506, i8* %\".10\"), !dbg !364\n  ret i32 %\".11\", !dbg !364\n}"
    },
    "tcsetattr_drain": {
      "hash": "a053589a659e656f",
      "sig_hash": "7e648f7dec9161db",
      "ir": "define i32 @\"tcsetattr_drain\"(i32 %\"fd.arg\", %\"struct.ritz_module_1.Termios\"* %\"termios_p.arg\") alignstack(16) !dbg !80\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !365, metadata !7), !dbg !366\n  %\"termios_p\" = alloca %\"struct.ritz_module_1.Termios\"*\n  store %\"struct.ritz_module_1.Termios\"* %\"termios_p.arg\", %\"struct.ritz_module_1.Termios\"** %\"termios_p\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Termios\"** %\"termios_p\", metadata !367, metadata !7), !dbg !366\n  %\".8\" = load i32, i32* %\"fd\", !dbg !368\n  %\".9\" = load %\"struct.ritz_module_1.Termios\"*, %\"struct.ritz_module_1.Termios\"** %\"termios_p\", !dbg !368\n  %\".10\" = bitcast %\"struct.ritz_module_1.Termios\"* %\".9\" to i8* , !dbg !368\n  %\".11\" = call i32 @\"sys_ioctl\"(i32 %\".8\", i64 21507, i8* %\".10\"), !dbg !368\n  ret i32 %\".11\", !dbg !368\n}"
    },
    "tcsetattr_flush": {
      "hash": "95ef6b910db82dc7",
      "sig_hash": "da18e170b05c2a31",
      "ir": "define i32 @\"tcsetattr_flush\"(i32 %\"fd.arg\", %\"struct.ritz_module_1.Termios\"* %\"termios_p.arg\") alignstack(16) !dbg !81\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !369, metadata !7), !dbg !370\n  %\"termios_p\" = alloca %\"struct.ritz_module_1.Termios\"*\n  store %\"struct.ritz_module_1.Termios\"* %\"termios_p.arg\", %\"struct.ritz_module_1.Termios\"** %\"termios_p\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Termios\"** %\"termios_p\", metadata !371, metadata !7), !dbg !370\n  %\".8\" = load i32, i32* %\"fd\", !dbg !372\n  %\".9\" = load %\"struct.ritz_module_1.Termios\"*, %\"struct.ritz_module_1.Termios\"** %\"termios_p\", !dbg !372\n  %\".10\" = bitcast %\"struct.ritz_module_1.Termios\"* %\".9\" to i8* , !dbg !372\n  %\".11\" = call i32 @\"sys_ioctl\"(i32 %\".8\", i64 21508, i8* %\".10\"), !dbg !372\n  ret i32 %\".11\", !dbg !372\n}"
    },
    "get_winsize": {
      "hash": "7fa92f52198fd027",
      "sig_hash": "6bb53c2104c86d4f",
      "ir": "define i32 @\"get_winsize\"(i32 %\"fd.arg\", %\"struct.ritz_module_1.Winsize\"* %\"ws.arg\") alignstack(16) !dbg !82\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !373, metadata !7), !dbg !374\n  %\"ws\" = alloca %\"struct.ritz_module_1.Winsize\"*\n  store %\"struct.ritz_module_1.Winsize\"* %\"ws.arg\", %\"struct.ritz_module_1.Winsize\"** %\"ws\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Winsize\"** %\"ws\", metadata !377, metadata !7), !dbg !374\n  %\".8\" = load i32, i32* %\"fd\", !dbg !378\n  %\".9\" = load %\"struct.ritz_module_1.Winsize\"*, %\"struct.ritz_module_1.Winsize\"** %\"ws\", !dbg !378\n  %\".10\" = bitcast %\"struct.ritz_module_1.Winsize\"* %\".9\" to i8* , !dbg !378\n  %\".11\" = call i32 @\"sys_ioctl\"(i32 %\".8\", i64 21523, i8* %\".10\"), !dbg !378\n  ret i32 %\".11\", !dbg !378\n}"
    },
    "sys_tty_getattr": {
      "hash": "e130e6a205397e5c",
      "sig_hash": "4f49076d61beafcb",
      "ir": ""
    },
    "sys_tty_setattr": {
      "hash": "f5c7d146c179a69e",
      "sig_hash": "96941e6ca2e0b783",
      "ir": ""
    }
  },
  "imports": []
}
