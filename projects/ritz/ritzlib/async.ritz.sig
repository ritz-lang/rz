{
  "source_hash": "3e74ecde9af4d218",
  "functions": {
    "poll_is_ready": {
      "hash": "8c4c6b5c3039fc5c",
      "sig_hash": "19f9a3231ccbb4ac",
      "ir": ""
    },
    "poll_is_pending": {
      "hash": "17e5ac0994e9435d",
      "sig_hash": "167ffc9ef1fb36b6",
      "ir": ""
    },
    "waker_wake": {
      "hash": "f9150f3e5ececa8b",
      "sig_hash": "bd076c900da79072",
      "ir": "define i32 @\"waker_wake\"(%\"struct.ritz_module_1.Waker\"* %\"w.arg\") !dbg !17\n{\nentry:\n  %\"w\" = alloca %\"struct.ritz_module_1.Waker\"*\n  store %\"struct.ritz_module_1.Waker\"* %\"w.arg\", %\"struct.ritz_module_1.Waker\"** %\"w\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Waker\"** %\"w\", metadata !24, metadata !7), !dbg !25\n  %\".5\" = trunc i64 0 to i32 , !dbg !26\n  ret i32 0, !dbg !26\n}"
    },
    "waker_clone": {
      "hash": "1f35c96ca0254477",
      "sig_hash": "17052c52bb333658",
      "ir": "define %\"struct.ritz_module_1.Waker\" @\"waker_clone\"(%\"struct.ritz_module_1.Waker\"* %\"w.arg\") !dbg !18\n{\nentry:\n  %\"w\" = alloca %\"struct.ritz_module_1.Waker\"*\n  store %\"struct.ritz_module_1.Waker\"* %\"w.arg\", %\"struct.ritz_module_1.Waker\"** %\"w\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Waker\"** %\"w\", metadata !27, metadata !7), !dbg !28\n  %\".5\" = load %\"struct.ritz_module_1.Waker\"*, %\"struct.ritz_module_1.Waker\"** %\"w\", !dbg !29\n  %\".6\" = getelementptr %\"struct.ritz_module_1.Waker\", %\"struct.ritz_module_1.Waker\"* %\".5\", i32 0, i32 0 , !dbg !29\n  %\".7\" = load i8*, i8** %\".6\", !dbg !29\n  %\".8\" = load %\"struct.ritz_module_1.Waker\"*, %\"struct.ritz_module_1.Waker\"** %\"w\", !dbg !29\n  %\".9\" = getelementptr %\"struct.ritz_module_1.Waker\", %\"struct.ritz_module_1.Waker\"* %\".8\", i32 0, i32 1 , !dbg !29\n  %\".10\" = load i8*, i8** %\".9\", !dbg !29\n  %\".11\" = insertvalue %\"struct.ritz_module_1.Waker\" undef, i8* %\".7\", 0 , !dbg !29\n  %\".12\" = insertvalue %\"struct.ritz_module_1.Waker\" %\".11\", i8* %\".10\", 1 , !dbg !29\n  ret %\"struct.ritz_module_1.Waker\" %\".12\", !dbg !29\n}"
    },
    "context_waker": {
      "hash": "b54bd8c9aa4aabcf",
      "sig_hash": "b69f724574d0ed47",
      "ir": "define %\"struct.ritz_module_1.Waker\"* @\"context_waker\"(%\"struct.ritz_module_1.Context\"* %\"cx.arg\") !dbg !19\n{\nentry:\n  %\"cx\" = alloca %\"struct.ritz_module_1.Context\"*\n  store %\"struct.ritz_module_1.Context\"* %\"cx.arg\", %\"struct.ritz_module_1.Context\"** %\"cx\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Context\"** %\"cx\", metadata !32, metadata !7), !dbg !33\n  %\".5\" = load %\"struct.ritz_module_1.Context\"*, %\"struct.ritz_module_1.Context\"** %\"cx\", !dbg !34\n  %\".6\" = getelementptr %\"struct.ritz_module_1.Context\", %\"struct.ritz_module_1.Context\"* %\".5\", i32 0, i32 0 , !dbg !34\n  %\".7\" = load %\"struct.ritz_module_1.Waker\"*, %\"struct.ritz_module_1.Waker\"** %\".6\", !dbg !34\n  ret %\"struct.ritz_module_1.Waker\"* %\".7\", !dbg !34\n}"
    },
    "executor_new": {
      "hash": "6d532adce42ac851",
      "sig_hash": "4a42e43de7a64eed",
      "ir": "define %\"struct.ritz_module_1.Executor\" @\"executor_new\"() !dbg !20\n{\nentry:\n  %\".2\" = trunc i64 0 to i32 , !dbg !35\n  %\".3\" = sub i64 0, 1, !dbg !35\n  %\".4\" = trunc i64 %\".3\" to i32 , !dbg !35\n  %\".5\" = trunc i64 0 to i32 , !dbg !35\n  %\".6\" = insertvalue %\"struct.ritz_module_1.Executor\" undef, i64 0, 0 , !dbg !35\n  %\".7\" = insertvalue %\"struct.ritz_module_1.Executor\" %\".6\", i32 %\".2\", 1 , !dbg !35\n  %\".8\" = insertvalue %\"struct.ritz_module_1.Executor\" %\".7\", i32 %\".4\", 2 , !dbg !35\n  %\".9\" = insertvalue %\"struct.ritz_module_1.Executor\" %\".8\", i8* null, 3 , !dbg !35\n  %\".10\" = insertvalue %\"struct.ritz_module_1.Executor\" %\".9\", i8* null, 4 , !dbg !35\n  %\".11\" = insertvalue %\"struct.ritz_module_1.Executor\" %\".10\", i32 %\".5\", 5 , !dbg !35\n  ret %\"struct.ritz_module_1.Executor\" %\".11\", !dbg !35\n}"
    },
    "block_on_placeholder": {
      "hash": "358db517c810ce48",
      "sig_hash": "b223ce983c35a893",
      "ir": "define i32 @\"block_on_placeholder\"() !dbg !21\n{\nentry:\n  %\".2\" = trunc i64 0 to i32 , !dbg !36\n  ret i32 %\".2\", !dbg !36\n}"
    }
  },
  "imports": []
}
