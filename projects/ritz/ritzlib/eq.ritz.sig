{
  "source_hash": "90f52a8c9cad0029",
  "functions": {
    "eq_i32": {
      "hash": "b2fb49513b7e4153",
      "sig_hash": "87861deae8ff9cce",
      "ir": "define i32 @\"eq_i32\"(i32 %\"a.arg\", i32 %\"b.arg\") alignstack(16) !dbg !17\n{\nentry:\n  %\"a\" = alloca i32\n  store i32 %\"a.arg\", i32* %\"a\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"a\", metadata !20, metadata !7), !dbg !21\n  %\"b\" = alloca i32\n  store i32 %\"b.arg\", i32* %\"b\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"b\", metadata !22, metadata !7), !dbg !21\n  %\".8\" = load i32, i32* %\"a\", !dbg !23\n  %\".9\" = load i32, i32* %\"b\", !dbg !23\n  %\".10\" = icmp eq i32 %\".8\", %\".9\" , !dbg !23\n  br i1 %\".10\", label %\"if.then\", label %\"if.end\", !dbg !23\nif.then:\n  %\".12\" = trunc i64 1 to i32 , !dbg !24\n  ret i32 %\".12\", !dbg !24\nif.end:\n  %\".14\" = trunc i64 0 to i32 , !dbg !25\n  ret i32 %\".14\", !dbg !25\n}"
    },
    "eq_i64": {
      "hash": "0c57c146fb6e73d3",
      "sig_hash": "4584ad9aa1ad9a73",
      "ir": "define i32 @\"eq_i64\"(i64 %\"a.arg\", i64 %\"b.arg\") alignstack(16) !dbg !18\n{\nentry:\n  %\"a\" = alloca i64\n  store i64 %\"a.arg\", i64* %\"a\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"a\", metadata !26, metadata !7), !dbg !27\n  %\"b\" = alloca i64\n  store i64 %\"b.arg\", i64* %\"b\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"b\", metadata !28, metadata !7), !dbg !27\n  %\".8\" = load i64, i64* %\"a\", !dbg !29\n  %\".9\" = load i64, i64* %\"b\", !dbg !29\n  %\".10\" = icmp eq i64 %\".8\", %\".9\" , !dbg !29\n  br i1 %\".10\", label %\"if.then\", label %\"if.end\", !dbg !29\nif.then:\n  %\".12\" = trunc i64 1 to i32 , !dbg !30\n  ret i32 %\".12\", !dbg !30\nif.end:\n  %\".14\" = trunc i64 0 to i32 , !dbg !31\n  ret i32 %\".14\", !dbg !31\n}"
    },
    "eq_u64": {
      "hash": "bbd2cc45e8087a41",
      "sig_hash": "1504314d7ab0d771",
      "ir": "define i32 @\"eq_u64\"(i64 %\"a.arg\", i64 %\"b.arg\") alignstack(16) !dbg !19\n{\nentry:\n  %\"a\" = alloca i64\n  store i64 %\"a.arg\", i64* %\"a\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"a\", metadata !32, metadata !7), !dbg !33\n  %\"b\" = alloca i64\n  store i64 %\"b.arg\", i64* %\"b\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"b\", metadata !34, metadata !7), !dbg !33\n  %\".8\" = load i64, i64* %\"a\", !dbg !35\n  %\".9\" = load i64, i64* %\"b\", !dbg !35\n  %\".10\" = icmp eq i64 %\".8\", %\".9\" , !dbg !35\n  br i1 %\".10\", label %\"if.then\", label %\"if.end\", !dbg !35\nif.then:\n  %\".12\" = trunc i64 1 to i32 , !dbg !36\n  ret i32 %\".12\", !dbg !36\nif.end:\n  %\".14\" = trunc i64 0 to i32 , !dbg !37\n  ret i32 %\".14\", !dbg !37\n}"
    }
  },
  "imports": []
}
