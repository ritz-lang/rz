{
  "source_hash": "f85d2fe134cd0fcd",
  "functions": {
    "test_closure_no_capture": {
      "hash": "ce098481d0e86364",
      "ir": "define internal i32 @\"test_closure_no_capture\"() !dbg !17\n{\nentry:\n  %\".2\" = trunc i64 5 to i32 , !dbg !25\n  %\".3\" = call i32 @\"__closure_1\"(i32 %\".2\"), !dbg !25\n  %\".4\" = sext i32 %\".3\" to i64 , !dbg !25\n  %\".5\" = icmp ne i64 %\".4\", 10 , !dbg !25\n  br i1 %\".5\", label %\"if.then\", label %\"if.end\", !dbg !25\nif.then:\n  %\".7\" = trunc i64 1 to i32 , !dbg !26\n  ret i32 %\".7\", !dbg !26\nif.end:\n  %\".9\" = trunc i64 0 to i32 , !dbg !27\n  %\".10\" = call i32 @\"__closure_1\"(i32 %\".9\"), !dbg !27\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !27\n  %\".12\" = icmp ne i64 %\".11\", 0 , !dbg !27\n  br i1 %\".12\", label %\"if.then.1\", label %\"if.end.1\", !dbg !27\nif.then.1:\n  %\".14\" = trunc i64 2 to i32 , !dbg !28\n  ret i32 %\".14\", !dbg !28\nif.end.1:\n  %\".16\" = trunc i64 0 to i32 , !dbg !29\n  ret i32 %\".16\", !dbg !29\n}"
    },
    "test_lambda_explicit": {
      "hash": "3d6b9f917898285d",
      "ir": "define internal i32 @\"test_lambda_explicit\"() !dbg !18\n{\nentry:\n  %\".2\" = trunc i64 3 to i32 , !dbg !31\n  %\".3\" = trunc i64 4 to i32 , !dbg !31\n  %\".4\" = call i32 @\"__closure_2\"(i32 %\".2\", i32 %\".3\"), !dbg !31\n  %\".5\" = sext i32 %\".4\" to i64 , !dbg !31\n  %\".6\" = icmp ne i64 %\".5\", 7 , !dbg !31\n  br i1 %\".6\", label %\"if.then\", label %\"if.end\", !dbg !31\nif.then:\n  %\".8\" = trunc i64 1 to i32 , !dbg !32\n  ret i32 %\".8\", !dbg !32\nif.end:\n  %\".10\" = trunc i64 0 to i32 , !dbg !33\n  ret i32 %\".10\", !dbg !33\n}"
    },
    "apply": {
      "hash": "30c278ecb5494dc1",
      "ir": "define internal i32 @\"apply\"(i32 (i32)* %\"f.arg\", i32 %\"x.arg\") !dbg !19\n{\nentry:\n  %\"f\" = alloca i32 (i32)*\n  store i32 (i32)* %\"f.arg\", i32 (i32)** %\"f\"\n  %\"x\" = alloca i32\n  store i32 %\"x.arg\", i32* %\"x\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"x\", metadata !34, metadata !7), !dbg !35\n  %\".7\" = load i32 (i32)*, i32 (i32)** %\"f\", !dbg !36\n  %\".8\" = load i32, i32* %\"x\", !dbg !36\n  %\".9\" = call i32 %\".7\"(i32 %\".8\"), !dbg !36\n  ret i32 %\".9\", !dbg !36\n}"
    },
    "test_closure_as_arg": {
      "hash": "7de4c06ade0900b0",
      "ir": "define internal i32 @\"test_closure_as_arg\"() !dbg !20\n{\nentry:\n  %\".2\" = trunc i64 21 to i32 , !dbg !38\n  %\".3\" = call i32 @\"apply\"(i32 (i32)* @\"__closure_3\", i32 %\".2\"), !dbg !38\n  %\".4\" = sext i32 %\".3\" to i64 , !dbg !38\n  %\".5\" = icmp ne i64 %\".4\", 42 , !dbg !38\n  br i1 %\".5\", label %\"if.then\", label %\"if.end\", !dbg !38\nif.then:\n  %\".7\" = trunc i64 1 to i32 , !dbg !39\n  ret i32 %\".7\", !dbg !39\nif.end:\n  %\".9\" = trunc i64 0 to i32 , !dbg !40\n  ret i32 %\".9\", !dbg !40\n}"
    },
    "test_multiple_closures": {
      "hash": "16d1fb8d8fa7f1bc",
      "ir": "define internal i32 @\"test_multiple_closures\"() !dbg !21\n{\nentry:\n  %\".2\" = trunc i64 5 to i32 , !dbg !43\n  %\".3\" = call i32 @\"__closure_4\"(i32 %\".2\"), !dbg !43\n  %\".4\" = sext i32 %\".3\" to i64 , !dbg !43\n  %\".5\" = icmp ne i64 %\".4\", 6 , !dbg !43\n  br i1 %\".5\", label %\"if.then\", label %\"if.end\", !dbg !43\nif.then:\n  %\".7\" = trunc i64 1 to i32 , !dbg !44\n  ret i32 %\".7\", !dbg !44\nif.end:\n  %\".9\" = trunc i64 5 to i32 , !dbg !45\n  %\".10\" = call i32 @\"__closure_5\"(i32 %\".9\"), !dbg !45\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !45\n  %\".12\" = icmp ne i64 %\".11\", 4 , !dbg !45\n  br i1 %\".12\", label %\"if.then.1\", label %\"if.end.1\", !dbg !45\nif.then.1:\n  %\".14\" = trunc i64 2 to i32 , !dbg !46\n  ret i32 %\".14\", !dbg !46\nif.end.1:\n  %\".16\" = trunc i64 0 to i32 , !dbg !47\n  ret i32 %\".16\", !dbg !47\n}"
    },
    "test_closure_bool": {
      "hash": "59c7dfa49933deab",
      "ir": "define internal i32 @\"test_closure_bool\"() !dbg !22\n{\nentry:\n  %\".2\" = trunc i64 5 to i32 , !dbg !49\n  %\".3\" = call i1 @\"__closure_6\"(i32 %\".2\"), !dbg !49\n  %\".4\" = icmp eq i1 %\".3\", 0 , !dbg !49\n  br i1 %\".4\", label %\"if.then\", label %\"if.end\", !dbg !49\nif.then:\n  %\".6\" = trunc i64 1 to i32 , !dbg !50\n  ret i32 %\".6\", !dbg !50\nif.end:\n  %\".8\" = sub i64 0, 5, !dbg !51\n  %\".9\" = trunc i64 %\".8\" to i32 , !dbg !51\n  %\".10\" = call i1 @\"__closure_6\"(i32 %\".9\"), !dbg !51\n  %\".11\" = icmp eq i1 %\".10\", 1 , !dbg !51\n  br i1 %\".11\", label %\"if.then.1\", label %\"if.end.1\", !dbg !51\nif.then.1:\n  %\".13\" = trunc i64 2 to i32 , !dbg !52\n  ret i32 %\".13\", !dbg !52\nif.end.1:\n  %\".15\" = trunc i64 0 to i32 , !dbg !53\n  %\".16\" = call i1 @\"__closure_6\"(i32 %\".15\"), !dbg !53\n  %\".17\" = icmp eq i1 %\".16\", 1 , !dbg !53\n  br i1 %\".17\", label %\"if.then.2\", label %\"if.end.2\", !dbg !53\nif.then.2:\n  %\".19\" = trunc i64 3 to i32 , !dbg !54\n  ret i32 %\".19\", !dbg !54\nif.end.2:\n  %\".21\" = trunc i64 0 to i32 , !dbg !55\n  ret i32 %\".21\", !dbg !55\n}"
    },
    "main": {
      "hash": "3852a8190469ae1a",
      "ir": "define i32 @\"main\"() !dbg !23\n{\nentry:\n  %\".2\" = trunc i64 0 to i32 , !dbg !56\n  ret i32 %\".2\", !dbg !56\n}"
    }
  },
  "imports": []
}
