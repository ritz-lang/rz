{
  "source_hash": "7dbdc796f0fa1ee1",
  "functions": {
    "vec_new": {
      "hash": "b1dcd16cb1851a64",
      "sig_hash": "4f13265f1d2f17a1",
      "ir": ""
    },
    "vec_with_cap": {
      "hash": "90f5f8942fc2c288",
      "sig_hash": "831669a5facfe90f",
      "ir": ""
    },
    "vec_drop": {
      "hash": "65b8aca7dbb98e95",
      "sig_hash": "bcb90dde8353b8a3",
      "ir": ""
    },
    "vec_valid": {
      "hash": "2046f388e58cdb9e",
      "sig_hash": "a62aa23a7d392115",
      "ir": ""
    },
    "vec_len": {
      "hash": "51e6166360b5991f",
      "sig_hash": "7ac655a2fd021979",
      "ir": ""
    },
    "vec_cap": {
      "hash": "89faab9e33c64abc",
      "sig_hash": "907563ba625f133b",
      "ir": ""
    },
    "vec_is_empty": {
      "hash": "ee891bb4bbe615f9",
      "sig_hash": "a57cd5fce6ff5ab3",
      "ir": ""
    },
    "vec_grow": {
      "hash": "274f6b4ccaef895b",
      "sig_hash": "1a6f909d601506ed",
      "ir": ""
    },
    "vec_ensure_cap": {
      "hash": "eefb7adaf2f5d175",
      "sig_hash": "b755c9d644c019ac",
      "ir": ""
    },
    "vec_push": {
      "hash": "05f9df8d13b5639e",
      "sig_hash": "eea3d3ff8c25e635",
      "ir": ""
    },
    "vec_pop": {
      "hash": "48fe9814ff5d5cbd",
      "sig_hash": "fc90a6890b2fc432",
      "ir": ""
    },
    "vec_get": {
      "hash": "748ab1c4d5951d19",
      "sig_hash": "907e8ce92bbca77d",
      "ir": ""
    },
    "vec_get_ptr": {
      "hash": "4f98a083523ef74b",
      "sig_hash": "ec5751f8725502cb",
      "ir": ""
    },
    "vec_set": {
      "hash": "f05ee38ee34e9839",
      "sig_hash": "491c4da82827ac42",
      "ir": ""
    },
    "vec_clear": {
      "hash": "f417e3ebad94311d",
      "sig_hash": "24a7678c84af1475",
      "ir": ""
    },
    "vec_first": {
      "hash": "41ad08d8aaeb4835",
      "sig_hash": "51e0576585421d9c",
      "ir": ""
    },
    "vec_last": {
      "hash": "cc5f1bd92257412b",
      "sig_hash": "498e3bbf8b6bdb29",
      "ir": ""
    },
    "vec_as_ptr": {
      "hash": "c5d48f5b37c30521",
      "sig_hash": "4ab2b23d72840cf8",
      "ir": ""
    },
    "vec_slice": {
      "hash": "4f17ad942008e95c",
      "sig_hash": "ee57d6b71bac6211",
      "ir": ""
    },
    "vec_push_bytes": {
      "hash": "8b8768fe428579bc",
      "sig_hash": "0d9016ad3c22de41",
      "ir": ""
    },
    "vec_push_str": {
      "hash": "eaa7403ed1ea081c",
      "sig_hash": "2974dc9ce8e3d968",
      "ir": "define i32 @\"vec_push_str\"(%\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", i8* %\"s.arg\") alignstack(16) !dbg !17\n{\nentry:\n  %\"i.addr\" = alloca i64, !dbg !34\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", metadata !30, metadata !7), !dbg !31\n  %\"s\" = alloca i8*\n  store i8* %\"s.arg\", i8** %\"s\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"s\", metadata !33, metadata !7), !dbg !31\n  store i64 0, i64* %\"i.addr\", !dbg !34\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"i.addr\", metadata !35, metadata !7), !dbg !36\n  br label %\"while.cond\", !dbg !37\nwhile.cond:\n  %\".10\" = load i8*, i8** %\"s\", !dbg !37\n  %\".11\" = load i64, i64* %\"i.addr\", !dbg !37\n  %\".12\" = getelementptr i8, i8* %\".10\", i64 %\".11\" , !dbg !37\n  %\".13\" = load i8, i8* %\".12\", !dbg !37\n  %\".14\" = zext i8 %\".13\" to i64 , !dbg !37\n  %\".15\" = icmp ne i64 %\".14\", 0 , !dbg !37\n  br i1 %\".15\", label %\"while.body\", label %\"while.end\", !dbg !37\nwhile.body:\n  %\".17\" = load i8*, i8** %\"s\", !dbg !38\n  %\".18\" = load i64, i64* %\"i.addr\", !dbg !38\n  %\".19\" = getelementptr i8, i8* %\".17\", i64 %\".18\" , !dbg !38\n  %\".20\" = load i8, i8* %\".19\", !dbg !38\n  %\".21\" = call i32 @\"vec_push$u8\"(%\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", i8 %\".20\"), !dbg !38\n  %\".22\" = sext i32 %\".21\" to i64 , !dbg !38\n  %\".23\" = icmp ne i64 %\".22\", 0 , !dbg !38\n  br i1 %\".23\", label %\"if.then\", label %\"if.end\", !dbg !38\nwhile.end:\n  %\".32\" = trunc i64 0 to i32 , !dbg !41\n  ret i32 %\".32\", !dbg !41\nif.then:\n  %\".25\" = sub i64 0, 1, !dbg !39\n  %\".26\" = trunc i64 %\".25\" to i32 , !dbg !39\n  ret i32 %\".26\", !dbg !39\nif.end:\n  %\".28\" = load i64, i64* %\"i.addr\", !dbg !40\n  %\".29\" = add i64 %\".28\", 1, !dbg !40\n  store i64 %\".29\", i64* %\"i.addr\", !dbg !40\n  br label %\"while.cond\", !dbg !40\n}"
    },
    "vec_as_str": {
      "hash": "7f57c33afface204",
      "sig_hash": "ef90c55626c57292",
      "ir": "define i8* @\"vec_as_str\"(%\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\") alignstack(16) !dbg !18\n{\nentry:\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", metadata !42, metadata !7), !dbg !43\n  %\".4\" = getelementptr %\"struct.ritz_module_1.Vec$u8\", %\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", i32 0, i32 1 , !dbg !44\n  %\".5\" = load i64, i64* %\".4\", !dbg !44\n  %\".6\" = add i64 %\".5\", 1, !dbg !44\n  %\".7\" = call i32 @\"vec_ensure_cap$u8\"(%\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", i64 %\".6\"), !dbg !44\n  %\".8\" = sext i32 %\".7\" to i64 , !dbg !44\n  %\".9\" = icmp ne i64 %\".8\", 0 , !dbg !44\n  br i1 %\".9\", label %\"if.then\", label %\"if.end\", !dbg !44\nif.then:\n  ret i8* null, !dbg !45\nif.end:\n  %\".12\" = getelementptr %\"struct.ritz_module_1.Vec$u8\", %\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", i32 0, i32 0 , !dbg !46\n  %\".13\" = load i8*, i8** %\".12\", !dbg !46\n  %\".14\" = getelementptr %\"struct.ritz_module_1.Vec$u8\", %\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", i32 0, i32 1 , !dbg !46\n  %\".15\" = load i64, i64* %\".14\", !dbg !46\n  %\".16\" = getelementptr i8, i8* %\".13\", i64 %\".15\" , !dbg !46\n  %\".17\" = trunc i64 0 to i8 , !dbg !46\n  store i8 %\".17\", i8* %\".16\", !dbg !46\n  %\".19\" = getelementptr %\"struct.ritz_module_1.Vec$u8\", %\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", i32 0, i32 0 , !dbg !47\n  %\".20\" = load i8*, i8** %\".19\", !dbg !47\n  ret i8* %\".20\", !dbg !47\n}"
    },
    "vec_swap": {
      "hash": "b0fa687fe2a7d7e5",
      "sig_hash": "d185d1bb263765ac",
      "ir": ""
    },
    "vec_read_all_fd": {
      "hash": "266ecea7f27e6a5a",
      "sig_hash": "13d1c7b8024b8498",
      "ir": "define i64 @\"vec_read_all_fd\"(i32 %\"fd.arg\", %\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\") alignstack(16) !dbg !19\n{\nentry:\n  %\"fd\" = alloca i32\n  %\"temp.addr\" = alloca [4096 x i8], !dbg !52\n  %\"total.addr\" = alloca i64, !dbg !58\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !48, metadata !7), !dbg !49\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", metadata !50, metadata !7), !dbg !49\n  call void @\"llvm.dbg.declare\"(metadata [4096 x i8]* %\"temp.addr\", metadata !56, metadata !7), !dbg !57\n  store i64 0, i64* %\"total.addr\", !dbg !58\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"total.addr\", metadata !59, metadata !7), !dbg !60\n  br label %\"while.cond\", !dbg !61\nwhile.cond:\n  br i1 1, label %\"while.body\", label %\"while.end\", !dbg !61\nwhile.body:\n  %\".12\" = load i32, i32* %\"fd\", !dbg !62\n  %\".13\" = getelementptr [4096 x i8], [4096 x i8]* %\"temp.addr\", i32 0, i64 0 , !dbg !62\n  %\".14\" = call i64 @\"sys_read\"(i32 %\".12\", i8* %\".13\", i64 4096), !dbg !62\n  %\".15\" = icmp slt i64 %\".14\", 0 , !dbg !63\n  br i1 %\".15\", label %\"if.then\", label %\"if.end\", !dbg !63\nwhile.end:\n  %\".33\" = load i64, i64* %\"total.addr\", !dbg !70\n  ret i64 %\".33\", !dbg !70\nif.then:\n  %\".17\" = sub i64 0, 1, !dbg !64\n  ret i64 %\".17\", !dbg !64\nif.end:\n  %\".19\" = icmp eq i64 %\".14\", 0 , !dbg !65\n  br i1 %\".19\", label %\"if.then.1\", label %\"if.end.1\", !dbg !65\nif.then.1:\n  br label %\"while.end\", !dbg !66\nif.end.1:\n  %\".22\" = getelementptr [4096 x i8], [4096 x i8]* %\"temp.addr\", i32 0, i64 0 , !dbg !67\n  %\".23\" = call i32 @\"vec_push_bytes$u8\"(%\"struct.ritz_module_1.Vec$u8\"* %\"v.arg\", i8* %\".22\", i64 %\".14\"), !dbg !67\n  %\".24\" = sext i32 %\".23\" to i64 , !dbg !67\n  %\".25\" = icmp ne i64 %\".24\", 0 , !dbg !67\n  br i1 %\".25\", label %\"if.then.2\", label %\"if.end.2\", !dbg !67\nif.then.2:\n  %\".27\" = sub i64 0, 1, !dbg !68\n  ret i64 %\".27\", !dbg !68\nif.end.2:\n  %\".29\" = load i64, i64* %\"total.addr\", !dbg !69\n  %\".30\" = add i64 %\".29\", %\".14\", !dbg !69\n  store i64 %\".30\", i64* %\"total.addr\", !dbg !69\n  br label %\"while.cond\", !dbg !69\n}"
    },
    "vec_find_lines": {
      "hash": "14f4618604ffb600",
      "sig_hash": "ad9a5526b3f41389",
      "ir": "define i32 @\"vec_find_lines\"(%\"struct.ritz_module_1.Vec$u8\"* %\"buf.arg\", %\"struct.ritz_module_1.Vec$LineBounds\"* %\"lines.arg\") alignstack(16) !dbg !20\n{\nentry:\n  %\"line_start.addr\" = alloca i64, !dbg !76\n  %\"i.addr\" = alloca i64, !dbg !79\n  %\"bounds.addr\" = alloca %\"struct.ritz_module_1.LineBounds\", !dbg !84\n  %\"bounds.addr.1\" = alloca %\"struct.ritz_module_1.LineBounds\", !dbg !95\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Vec$u8\"* %\"buf.arg\", metadata !71, metadata !7), !dbg !72\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Vec$LineBounds\"* %\"lines.arg\", metadata !75, metadata !7), !dbg !72\n  store i64 0, i64* %\"line_start.addr\", !dbg !76\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"line_start.addr\", metadata !77, metadata !7), !dbg !78\n  store i64 0, i64* %\"i.addr\", !dbg !79\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"i.addr\", metadata !80, metadata !7), !dbg !81\n  br label %\"while.cond\", !dbg !82\nwhile.cond:\n  %\".11\" = load i64, i64* %\"i.addr\", !dbg !82\n  %\".12\" = getelementptr %\"struct.ritz_module_1.Vec$u8\", %\"struct.ritz_module_1.Vec$u8\"* %\"buf.arg\", i32 0, i32 1 , !dbg !82\n  %\".13\" = load i64, i64* %\".12\", !dbg !82\n  %\".14\" = icmp slt i64 %\".11\", %\".13\" , !dbg !82\n  br i1 %\".14\", label %\"while.body\", label %\"while.end\", !dbg !82\nwhile.body:\n  %\".16\" = getelementptr %\"struct.ritz_module_1.Vec$u8\", %\"struct.ritz_module_1.Vec$u8\"* %\"buf.arg\", i32 0, i32 0 , !dbg !83\n  %\".17\" = load i8*, i8** %\".16\", !dbg !83\n  %\".18\" = load i64, i64* %\"i.addr\", !dbg !83\n  %\".19\" = getelementptr i8, i8* %\".17\", i64 %\".18\" , !dbg !83\n  %\".20\" = load i8, i8* %\".19\", !dbg !83\n  %\".21\" = icmp eq i8 %\".20\", 10 , !dbg !83\n  br i1 %\".21\", label %\"if.then\", label %\"if.end\", !dbg !83\nwhile.end:\n  %\".51\" = load i64, i64* %\"line_start.addr\", !dbg !94\n  %\".52\" = getelementptr %\"struct.ritz_module_1.Vec$u8\", %\"struct.ritz_module_1.Vec$u8\"* %\"buf.arg\", i32 0, i32 1 , !dbg !94\n  %\".53\" = load i64, i64* %\".52\", !dbg !94\n  %\".54\" = icmp slt i64 %\".51\", %\".53\" , !dbg !94\n  br i1 %\".54\", label %\"if.then.2\", label %\"if.end.2\", !dbg !94\nif.then:\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr\", metadata !86, metadata !7), !dbg !87\n  %\".24\" = load i64, i64* %\"line_start.addr\", !dbg !88\n  %\".25\" = load %\"struct.ritz_module_1.LineBounds\", %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr\", !dbg !88\n  %\".26\" = getelementptr %\"struct.ritz_module_1.LineBounds\", %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr\", i32 0, i32 0 , !dbg !88\n  store i64 %\".24\", i64* %\".26\", !dbg !88\n  %\".28\" = load i64, i64* %\"i.addr\", !dbg !89\n  %\".29\" = load i64, i64* %\"line_start.addr\", !dbg !89\n  %\".30\" = sub i64 %\".28\", %\".29\", !dbg !89\n  %\".31\" = add i64 %\".30\", 1, !dbg !89\n  %\".32\" = load %\"struct.ritz_module_1.LineBounds\", %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr\", !dbg !89\n  %\".33\" = getelementptr %\"struct.ritz_module_1.LineBounds\", %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr\", i32 0, i32 1 , !dbg !89\n  store i64 %\".31\", i64* %\".33\", !dbg !89\n  %\".35\" = load %\"struct.ritz_module_1.LineBounds\", %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr\", !dbg !90\n  %\".36\" = call i32 @\"vec_push$LineBounds\"(%\"struct.ritz_module_1.Vec$LineBounds\"* %\"lines.arg\", %\"struct.ritz_module_1.LineBounds\" %\".35\"), !dbg !90\n  %\".37\" = sext i32 %\".36\" to i64 , !dbg !90\n  %\".38\" = icmp ne i64 %\".37\", 0 , !dbg !90\n  br i1 %\".38\", label %\"if.then.1\", label %\"if.end.1\", !dbg !90\nif.end:\n  %\".47\" = load i64, i64* %\"i.addr\", !dbg !93\n  %\".48\" = add i64 %\".47\", 1, !dbg !93\n  store i64 %\".48\", i64* %\"i.addr\", !dbg !93\n  br label %\"while.cond\", !dbg !93\nif.then.1:\n  %\".40\" = sub i64 0, 1, !dbg !91\n  %\".41\" = trunc i64 %\".40\" to i32 , !dbg !91\n  ret i32 %\".41\", !dbg !91\nif.end.1:\n  %\".43\" = load i64, i64* %\"i.addr\", !dbg !92\n  %\".44\" = add i64 %\".43\", 1, !dbg !92\n  store i64 %\".44\", i64* %\"line_start.addr\", !dbg !92\n  br label %\"if.end\", !dbg !92\nif.then.2:\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr.1\", metadata !96, metadata !7), !dbg !97\n  %\".57\" = load i64, i64* %\"line_start.addr\", !dbg !98\n  %\".58\" = load %\"struct.ritz_module_1.LineBounds\", %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr.1\", !dbg !98\n  %\".59\" = getelementptr %\"struct.ritz_module_1.LineBounds\", %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr.1\", i32 0, i32 0 , !dbg !98\n  store i64 %\".57\", i64* %\".59\", !dbg !98\n  %\".61\" = getelementptr %\"struct.ritz_module_1.Vec$u8\", %\"struct.ritz_module_1.Vec$u8\"* %\"buf.arg\", i32 0, i32 1 , !dbg !99\n  %\".62\" = load i64, i64* %\".61\", !dbg !99\n  %\".63\" = load i64, i64* %\"line_start.addr\", !dbg !99\n  %\".64\" = sub i64 %\".62\", %\".63\", !dbg !99\n  %\".65\" = load %\"struct.ritz_module_1.LineBounds\", %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr.1\", !dbg !99\n  %\".66\" = getelementptr %\"struct.ritz_module_1.LineBounds\", %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr.1\", i32 0, i32 1 , !dbg !99\n  store i64 %\".64\", i64* %\".66\", !dbg !99\n  %\".68\" = load %\"struct.ritz_module_1.LineBounds\", %\"struct.ritz_module_1.LineBounds\"* %\"bounds.addr.1\", !dbg !99\n  %\".69\" = call i32 @\"vec_push$LineBounds\"(%\"struct.ritz_module_1.Vec$LineBounds\"* %\"lines.arg\", %\"struct.ritz_module_1.LineBounds\" %\".68\"), !dbg !99\n  %\".70\" = sext i32 %\".69\" to i64 , !dbg !99\n  %\".71\" = icmp ne i64 %\".70\", 0 , !dbg !99\n  br i1 %\".71\", label %\"if.then.3\", label %\"if.end.3\", !dbg !99\nif.end.2:\n  %\".77\" = trunc i64 0 to i32 , !dbg !101\n  ret i32 %\".77\", !dbg !101\nif.then.3:\n  %\".73\" = sub i64 0, 1, !dbg !100\n  %\".74\" = trunc i64 %\".73\" to i32 , !dbg !100\n  ret i32 %\".74\", !dbg !100\nif.end.3:\n  br label %\"if.end.2\", !dbg !100\n}"
    }
  },
  "imports": []
}
