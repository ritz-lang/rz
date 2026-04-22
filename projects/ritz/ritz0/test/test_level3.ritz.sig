{
  "source_hash": "f19a42077445a04a",
  "functions": {
    "add": {
      "hash": "15bf1fbbfec1f6ad",
      "ir": "define internal i32 @\"add\"(i32 %\"a.arg\", i32 %\"b.arg\") !dbg !17\n{\nentry:\n  %\"a\" = alloca i32\n  store i32 %\"a.arg\", i32* %\"a\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"a\", metadata !36, metadata !7), !dbg !37\n  %\"b\" = alloca i32\n  store i32 %\"b.arg\", i32* %\"b\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"b\", metadata !38, metadata !7), !dbg !37\n  %\".8\" = load i32, i32* %\"a\", !dbg !39\n  %\".9\" = load i32, i32* %\"b\", !dbg !39\n  %\".10\" = add i32 %\".8\", %\".9\", !dbg !39\n  ret i32 %\".10\", !dbg !39\n}"
    },
    "sub": {
      "hash": "1f7eb2af51c6b760",
      "ir": "define internal i32 @\"sub\"(i32 %\"a.arg\", i32 %\"b.arg\") !dbg !18\n{\nentry:\n  %\"a\" = alloca i32\n  store i32 %\"a.arg\", i32* %\"a\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"a\", metadata !40, metadata !7), !dbg !41\n  %\"b\" = alloca i32\n  store i32 %\"b.arg\", i32* %\"b\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"b\", metadata !42, metadata !7), !dbg !41\n  %\".8\" = load i32, i32* %\"a\", !dbg !43\n  %\".9\" = load i32, i32* %\"b\", !dbg !43\n  %\".10\" = sub i32 %\".8\", %\".9\", !dbg !43\n  ret i32 %\".10\", !dbg !43\n}"
    },
    "mul": {
      "hash": "f7bb0ee66762e887",
      "ir": "define internal i32 @\"mul\"(i32 %\"a.arg\", i32 %\"b.arg\") !dbg !19\n{\nentry:\n  %\"a\" = alloca i32\n  store i32 %\"a.arg\", i32* %\"a\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"a\", metadata !44, metadata !7), !dbg !45\n  %\"b\" = alloca i32\n  store i32 %\"b.arg\", i32* %\"b\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"b\", metadata !46, metadata !7), !dbg !45\n  %\".8\" = load i32, i32* %\"a\", !dbg !47\n  %\".9\" = load i32, i32* %\"b\", !dbg !47\n  %\".10\" = mul i32 %\".8\", %\".9\", !dbg !47\n  ret i32 %\".10\", !dbg !47\n}"
    },
    "identity": {
      "hash": "2fa04bee5e0e796c",
      "ir": "define internal i32 @\"identity\"(i32 %\"x.arg\") !dbg !20\n{\nentry:\n  %\"x\" = alloca i32\n  store i32 %\"x.arg\", i32* %\"x\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"x\", metadata !48, metadata !7), !dbg !49\n  %\".5\" = load i32, i32* %\"x\", !dbg !50\n  ret i32 %\".5\", !dbg !50\n}"
    },
    "square": {
      "hash": "06f2f87650ab7246",
      "ir": "define internal i32 @\"square\"(i32 %\"x.arg\") !dbg !21\n{\nentry:\n  %\"x\" = alloca i32\n  store i32 %\"x.arg\", i32* %\"x\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"x\", metadata !51, metadata !7), !dbg !52\n  %\".5\" = load i32, i32* %\"x\", !dbg !53\n  %\".6\" = load i32, i32* %\"x\", !dbg !53\n  %\".7\" = mul i32 %\".5\", %\".6\", !dbg !53\n  ret i32 %\".7\", !dbg !53\n}"
    },
    "double": {
      "hash": "651aaaccf29a1ac5",
      "ir": "define internal i32 @\"double\"(i32 %\"x.arg\") !dbg !22\n{\nentry:\n  %\"x\" = alloca i32\n  store i32 %\"x.arg\", i32* %\"x\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"x\", metadata !54, metadata !7), !dbg !55\n  %\".5\" = load i32, i32* %\"x\", !dbg !56\n  %\".6\" = load i32, i32* %\"x\", !dbg !56\n  %\".7\" = add i32 %\".5\", %\".6\", !dbg !56\n  ret i32 %\".7\", !dbg !56\n}"
    },
    "abs_diff": {
      "hash": "c271fa5d0af30df8",
      "ir": "define internal i32 @\"abs_diff\"(i32 %\"a.arg\", i32 %\"b.arg\") !dbg !23\n{\nentry:\n  %\"a\" = alloca i32\n  store i32 %\"a.arg\", i32* %\"a\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"a\", metadata !57, metadata !7), !dbg !58\n  %\"b\" = alloca i32\n  store i32 %\"b.arg\", i32* %\"b\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"b\", metadata !59, metadata !7), !dbg !58\n  %\".8\" = load i32, i32* %\"a\", !dbg !60\n  %\".9\" = load i32, i32* %\"b\", !dbg !60\n  %\".10\" = icmp sgt i32 %\".8\", %\".9\" , !dbg !60\n  br i1 %\".10\", label %\"if.then\", label %\"if.else\", !dbg !60\nif.then:\n  %\".12\" = load i32, i32* %\"a\", !dbg !60\n  %\".13\" = load i32, i32* %\"b\", !dbg !60\n  %\".14\" = sub i32 %\".12\", %\".13\", !dbg !60\n  br label %\"if.end\", !dbg !60\nif.else:\n  %\".15\" = load i32, i32* %\"b\", !dbg !60\n  %\".16\" = load i32, i32* %\"a\", !dbg !60\n  %\".17\" = sub i32 %\".15\", %\".16\", !dbg !60\n  br label %\"if.end\", !dbg !60\nif.end:\n  %\".20\" = phi  i32 [%\".14\", %\"if.then\"], [%\".17\", %\"if.else\"] , !dbg !60\n  ret i32 %\".20\", !dbg !60\n}"
    },
    "fib": {
      "hash": "6eac60b171aab1c7",
      "ir": "define internal i32 @\"fib\"(i32 %\"n.arg\") !dbg !24\n{\nentry:\n  %\"n\" = alloca i32\n  store i32 %\"n.arg\", i32* %\"n\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"n\", metadata !61, metadata !7), !dbg !62\n  %\".5\" = load i32, i32* %\"n\", !dbg !63\n  %\".6\" = sext i32 %\".5\" to i64 , !dbg !63\n  %\".7\" = icmp slt i64 %\".6\", 2 , !dbg !63\n  br i1 %\".7\", label %\"if.then\", label %\"if.else\", !dbg !63\nif.then:\n  %\".9\" = load i32, i32* %\"n\", !dbg !63\n  br label %\"if.end\", !dbg !63\nif.else:\n  %\".10\" = load i32, i32* %\"n\", !dbg !63\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !63\n  %\".12\" = sub i64 %\".11\", 1, !dbg !63\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !63\n  %\".14\" = call i32 @\"fib\"(i32 %\".13\"), !dbg !63\n  %\".15\" = load i32, i32* %\"n\", !dbg !63\n  %\".16\" = sext i32 %\".15\" to i64 , !dbg !63\n  %\".17\" = sub i64 %\".16\", 2, !dbg !63\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !63\n  %\".19\" = call i32 @\"fib\"(i32 %\".18\"), !dbg !63\n  %\".20\" = add i32 %\".14\", %\".19\", !dbg !63\n  br label %\"if.end\", !dbg !63\nif.end:\n  %\".23\" = phi  i32 [%\".9\", %\"if.then\"], [%\".20\", %\"if.else\"] , !dbg !63\n  ret i32 %\".23\", !dbg !63\n}"
    },
    "test_simple_call": {
      "hash": "282a898774a9b723",
      "ir": "define internal i32 @\"test_simple_call\"() !dbg !25\n{\nentry:\n  %\".2\" = trunc i64 2 to i32 , !dbg !64\n  %\".3\" = trunc i64 3 to i32 , !dbg !64\n  %\".4\" = call i32 @\"add\"(i32 %\".2\", i32 %\".3\"), !dbg !64\n  %\".5\" = sext i32 %\".4\" to i64 , !dbg !64\n  %\".6\" = icmp eq i64 %\".5\", 5 , !dbg !64\n  br i1 %\".6\", label %\"assert.pass\", label %\"assert.fail\", !dbg !64\nassert.pass:\n  %\".10\" = trunc i64 0 to i32 , !dbg !65\n  ret i32 %\".10\", !dbg !65\nassert.fail:\n  %\".8\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !64\n  unreachable\n}"
    },
    "test_nested_call": {
      "hash": "f389e1a7b86e8bab",
      "ir": "define internal i32 @\"test_nested_call\"() !dbg !26\n{\nentry:\n  %\".2\" = trunc i64 1 to i32 , !dbg !66\n  %\".3\" = trunc i64 2 to i32 , !dbg !66\n  %\".4\" = call i32 @\"add\"(i32 %\".2\", i32 %\".3\"), !dbg !66\n  %\".5\" = trunc i64 3 to i32 , !dbg !66\n  %\".6\" = trunc i64 4 to i32 , !dbg !66\n  %\".7\" = call i32 @\"add\"(i32 %\".5\", i32 %\".6\"), !dbg !66\n  %\".8\" = call i32 @\"add\"(i32 %\".4\", i32 %\".7\"), !dbg !66\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !66\n  %\".10\" = icmp eq i64 %\".9\", 10 , !dbg !66\n  br i1 %\".10\", label %\"assert.pass\", label %\"assert.fail\", !dbg !66\nassert.pass:\n  %\".14\" = trunc i64 0 to i32 , !dbg !67\n  ret i32 %\".14\", !dbg !67\nassert.fail:\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !66\n  unreachable\n}"
    },
    "test_call_in_expression": {
      "hash": "b1382a9e55360091",
      "ir": "define internal i32 @\"test_call_in_expression\"() !dbg !27\n{\nentry:\n  %\".2\" = trunc i64 1 to i32 , !dbg !68\n  %\".3\" = trunc i64 2 to i32 , !dbg !68\n  %\".4\" = call i32 @\"add\"(i32 %\".2\", i32 %\".3\"), !dbg !68\n  %\".5\" = trunc i64 5 to i32 , !dbg !68\n  %\".6\" = trunc i64 3 to i32 , !dbg !68\n  %\".7\" = call i32 @\"sub\"(i32 %\".5\", i32 %\".6\"), !dbg !68\n  %\".8\" = add i32 %\".4\", %\".7\", !dbg !68\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !68\n  %\".10\" = icmp eq i64 %\".9\", 5 , !dbg !68\n  br i1 %\".10\", label %\"assert.pass\", label %\"assert.fail\", !dbg !68\nassert.pass:\n  %\".14\" = trunc i64 0 to i32 , !dbg !69\n  ret i32 %\".14\", !dbg !69\nassert.fail:\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !68\n  unreachable\n}"
    },
    "test_call_with_literals": {
      "hash": "56d0fcd4f30a774a",
      "ir": "define internal i32 @\"test_call_with_literals\"() !dbg !28\n{\nentry:\n  %\".2\" = trunc i64 6 to i32 , !dbg !70\n  %\".3\" = trunc i64 7 to i32 , !dbg !70\n  %\".4\" = call i32 @\"mul\"(i32 %\".2\", i32 %\".3\"), !dbg !70\n  %\".5\" = sext i32 %\".4\" to i64 , !dbg !70\n  %\".6\" = icmp eq i64 %\".5\", 42 , !dbg !70\n  br i1 %\".6\", label %\"assert.pass\", label %\"assert.fail\", !dbg !70\nassert.pass:\n  %\".10\" = trunc i64 0 to i32 , !dbg !71\n  ret i32 %\".10\", !dbg !71\nassert.fail:\n  %\".8\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !70\n  unreachable\n}"
    },
    "test_identity": {
      "hash": "c87d2ab2fa24631e",
      "ir": "define internal i32 @\"test_identity\"() !dbg !29\n{\nentry:\n  %\".2\" = trunc i64 42 to i32 , !dbg !72\n  %\".3\" = call i32 @\"identity\"(i32 %\".2\"), !dbg !72\n  %\".4\" = sext i32 %\".3\" to i64 , !dbg !72\n  %\".5\" = icmp eq i64 %\".4\", 42 , !dbg !72\n  br i1 %\".5\", label %\"assert.pass\", label %\"assert.fail\", !dbg !72\nassert.pass:\n  %\".9\" = trunc i64 0 to i32 , !dbg !73\n  ret i32 %\".9\", !dbg !73\nassert.fail:\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !72\n  unreachable\n}"
    },
    "test_square": {
      "hash": "2b283f78ce0403bd",
      "ir": "define internal i32 @\"test_square\"() !dbg !30\n{\nentry:\n  %\".2\" = trunc i64 5 to i32 , !dbg !74\n  %\".3\" = call i32 @\"square\"(i32 %\".2\"), !dbg !74\n  %\".4\" = sext i32 %\".3\" to i64 , !dbg !74\n  %\".5\" = icmp eq i64 %\".4\", 25 , !dbg !74\n  br i1 %\".5\", label %\"assert.pass\", label %\"assert.fail\", !dbg !74\nassert.pass:\n  %\".9\" = trunc i64 0 to i32 , !dbg !75\n  ret i32 %\".9\", !dbg !75\nassert.fail:\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !74\n  unreachable\n}"
    },
    "test_double": {
      "hash": "c195ab54ff9e085a",
      "ir": "define internal i32 @\"test_double\"() !dbg !31\n{\nentry:\n  %\".2\" = trunc i64 21 to i32 , !dbg !76\n  %\".3\" = call i32 @\"double\"(i32 %\".2\"), !dbg !76\n  %\".4\" = sext i32 %\".3\" to i64 , !dbg !76\n  %\".5\" = icmp eq i64 %\".4\", 42 , !dbg !76\n  br i1 %\".5\", label %\"assert.pass\", label %\"assert.fail\", !dbg !76\nassert.pass:\n  %\".9\" = trunc i64 0 to i32 , !dbg !77\n  ret i32 %\".9\", !dbg !77\nassert.fail:\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !76\n  unreachable\n}"
    },
    "test_abs_diff": {
      "hash": "6dea3dceac6bdb23",
      "ir": "define internal i32 @\"test_abs_diff\"() !dbg !32\n{\nentry:\n  %\".2\" = trunc i64 10 to i32 , !dbg !78\n  %\".3\" = trunc i64 7 to i32 , !dbg !78\n  %\".4\" = call i32 @\"abs_diff\"(i32 %\".2\", i32 %\".3\"), !dbg !78\n  %\".5\" = sext i32 %\".4\" to i64 , !dbg !78\n  %\".6\" = icmp eq i64 %\".5\", 3 , !dbg !78\n  br i1 %\".6\", label %\"assert.pass\", label %\"assert.fail\", !dbg !78\nassert.pass:\n  %\".10\" = trunc i64 7 to i32 , !dbg !79\n  %\".11\" = trunc i64 10 to i32 , !dbg !79\n  %\".12\" = call i32 @\"abs_diff\"(i32 %\".10\", i32 %\".11\"), !dbg !79\n  %\".13\" = sext i32 %\".12\" to i64 , !dbg !79\n  %\".14\" = icmp eq i64 %\".13\", 3 , !dbg !79\n  br i1 %\".14\", label %\"assert.pass.1\", label %\"assert.fail.1\", !dbg !79\nassert.fail:\n  %\".8\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !78\n  unreachable\nassert.pass.1:\n  %\".18\" = trunc i64 0 to i32 , !dbg !80\n  ret i32 %\".18\", !dbg !80\nassert.fail.1:\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !79\n  unreachable\n}"
    },
    "test_recursive_fib": {
      "hash": "5800420badfdd0c4",
      "ir": "define internal i32 @\"test_recursive_fib\"() !dbg !33\n{\nentry:\n  %\".2\" = trunc i64 0 to i32 , !dbg !81\n  %\".3\" = call i32 @\"fib\"(i32 %\".2\"), !dbg !81\n  %\".4\" = sext i32 %\".3\" to i64 , !dbg !81\n  %\".5\" = icmp eq i64 %\".4\", 0 , !dbg !81\n  br i1 %\".5\", label %\"assert.pass\", label %\"assert.fail\", !dbg !81\nassert.pass:\n  %\".9\" = trunc i64 1 to i32 , !dbg !82\n  %\".10\" = call i32 @\"fib\"(i32 %\".9\"), !dbg !82\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !82\n  %\".12\" = icmp eq i64 %\".11\", 1 , !dbg !82\n  br i1 %\".12\", label %\"assert.pass.1\", label %\"assert.fail.1\", !dbg !82\nassert.fail:\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !81\n  unreachable\nassert.pass.1:\n  %\".16\" = trunc i64 5 to i32 , !dbg !83\n  %\".17\" = call i32 @\"fib\"(i32 %\".16\"), !dbg !83\n  %\".18\" = sext i32 %\".17\" to i64 , !dbg !83\n  %\".19\" = icmp eq i64 %\".18\", 5 , !dbg !83\n  br i1 %\".19\", label %\"assert.pass.2\", label %\"assert.fail.2\", !dbg !83\nassert.fail.1:\n  %\".14\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !82\n  unreachable\nassert.pass.2:\n  %\".23\" = trunc i64 10 to i32 , !dbg !84\n  %\".24\" = call i32 @\"fib\"(i32 %\".23\"), !dbg !84\n  %\".25\" = sext i32 %\".24\" to i64 , !dbg !84\n  %\".26\" = icmp eq i64 %\".25\", 55 , !dbg !84\n  br i1 %\".26\", label %\"assert.pass.3\", label %\"assert.fail.3\", !dbg !84\nassert.fail.2:\n  %\".21\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !83\n  unreachable\nassert.pass.3:\n  %\".30\" = trunc i64 0 to i32 , !dbg !85\n  ret i32 %\".30\", !dbg !85\nassert.fail.3:\n  %\".28\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !84\n  unreachable\n}"
    },
    "test_call_with_var": {
      "hash": "de13b9dd5feb2b80",
      "ir": "define internal i32 @\"test_call_with_var\"() !dbg !34\n{\nentry:\n  %\"x.addr\" = alloca i32, !dbg !86\n  %\"y.addr\" = alloca i32, !dbg !89\n  %\".2\" = trunc i64 10 to i32 , !dbg !86\n  store i32 %\".2\", i32* %\"x.addr\", !dbg !86\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"x.addr\", metadata !87, metadata !7), !dbg !88\n  %\".5\" = trunc i64 20 to i32 , !dbg !89\n  store i32 %\".5\", i32* %\"y.addr\", !dbg !89\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"y.addr\", metadata !90, metadata !7), !dbg !91\n  %\".8\" = load i32, i32* %\"x.addr\", !dbg !92\n  %\".9\" = load i32, i32* %\"y.addr\", !dbg !92\n  %\".10\" = call i32 @\"add\"(i32 %\".8\", i32 %\".9\"), !dbg !92\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !92\n  %\".12\" = icmp eq i64 %\".11\", 30 , !dbg !92\n  br i1 %\".12\", label %\"assert.pass\", label %\"assert.fail\", !dbg !92\nassert.pass:\n  %\".16\" = trunc i64 0 to i32 , !dbg !93\n  ret i32 %\".16\", !dbg !93\nassert.fail:\n  %\".14\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !92\n  unreachable\n}"
    },
    "test_call_result_in_var": {
      "hash": "e6a2a418b7a85377",
      "ir": "define internal i32 @\"test_call_result_in_var\"() !dbg !35\n{\nentry:\n  %\".2\" = trunc i64 100 to i32 , !dbg !94\n  %\".3\" = trunc i64 200 to i32 , !dbg !94\n  %\".4\" = call i32 @\"add\"(i32 %\".2\", i32 %\".3\"), !dbg !94\n  %\".5\" = sext i32 %\".4\" to i64 , !dbg !95\n  %\".6\" = icmp eq i64 %\".5\", 300 , !dbg !95\n  br i1 %\".6\", label %\"assert.pass\", label %\"assert.fail\", !dbg !95\nassert.pass:\n  %\".10\" = trunc i64 0 to i32 , !dbg !96\n  ret i32 %\".10\", !dbg !96\nassert.fail:\n  %\".8\" = call i64 asm sideeffect \"syscall\", \"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 1), !dbg !95\n  unreachable\n}"
    }
  },
  "imports": []
}
