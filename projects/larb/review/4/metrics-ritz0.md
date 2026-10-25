# ritz-metrics: 28 files, 26415 SLOC, 971 functions

## Longest functions (top 25)

| fn | where | SLOC | CC | depth |
|---|---|---|---|---|
| _try_emit_simd_builtin | `projects/ritz/ritz0/emitter_llvmlite.py:8692` | 477 | 145 | 5 |
| _try_emit_simd_builtin | `projects/ritz/ritz0/emitter/calls.py:255` | 442 | 136 | 5 |
| _emit_stmt_inner | `projects/ritz/ritz0/emitter_llvmlite.py:4247` | 358 | 119 | 10 |
| _emit_stmt | `projects/ritz/ritz0/emitter/stmts.py:33` | 273 | 91 | 10 |
| _emit_expr | `projects/ritz/ritz0/emitter_llvmlite.py:5843` | 258 | 138 | 6 |
| _emit_call_inner | `projects/ritz/ritz0/emitter_llvmlite.py:8342` | 215 | 93 | 10 |
| _emit_method_call | `projects/ritz/ritz0/emitter_llvmlite.py:9752` | 213 | 97 | 6 |
| _emit_index | `projects/ritz/ritz0/emitter_llvmlite.py:6238` | 195 | 78 | 7 |
| _emit_expr | `projects/ritz/ritz0/emitter/exprs.py:18` | 193 | 104 | 6 |
| _emit_closure | `projects/ritz/ritz0/emitter_llvmlite.py:7589` | 162 | 33 | 5 |
| _emit_closure | `projects/ritz/ritz0/emitter/exprs.py:909` | 156 | 30 | 5 |
| _emit_call | `projects/ritz/ritz0/emitter/calls.py:17` | 152 | 67 | 5 |
| _emit_asm | `projects/ritz/ritz0/emitter_llvmlite.py:4958` | 150 | 38 | 5 |
| _register_items_from_metadata | `projects/ritz/ritz0/import_resolver.py:983` | 150 | 33 | 10 |
| _emit_asm | `projects/ritz/ritz0/emitter/stmts.py:604` | 149 | 38 | 5 |
| _emit_for_iterable | `projects/ritz/ritz0/emitter_llvmlite.py:5588` | 148 | 42 | 7 |
| compile_file | `projects/ritz/ritz0/ritz0.py:70` | 142 | 36 | 6 |
| _emit_field_access | `projects/ritz/ritz0/emitter_llvmlite.py:8090` | 141 | 57 | 6 |
| parse_primary | `projects/ritz/ritz0/parser.py:923` | 134 | 45 | 6 |
| parse_primary_expr | `projects/ritz/ritz0/parser_gen.py:2844` | 128 | 23 | 3 |
| convert_type | `projects/ritz/ritz0/parser_adapter.py:271` | 123 | 33 | 6 |
| extract_metadata | `projects/ritz/ritz0/metadata.py:190` | 122 | 27 | 5 |
| _convert_type | `projects/ritz/ritz0/emitter_llvmlite.py:10278` | 118 | 67 | 6 |
| _parse_type_primary | `projects/ritz/ritz0/parser.py:453` | 118 | 28 | 5 |
| _infer_ritz_type | `projects/ritz/ritz0/emitter_llvmlite.py:1093` | 114 | 63 | 7 |

## Highest cyclomatic complexity (top 25)

| fn | where | CC | SLOC | depth |
|---|---|---|---|---|
| _try_emit_simd_builtin | `projects/ritz/ritz0/emitter_llvmlite.py:8692` | 145 | 477 | 5 |
| _emit_expr | `projects/ritz/ritz0/emitter_llvmlite.py:5843` | 138 | 258 | 6 |
| _try_emit_simd_builtin | `projects/ritz/ritz0/emitter/calls.py:255` | 136 | 442 | 5 |
| _emit_stmt_inner | `projects/ritz/ritz0/emitter_llvmlite.py:4247` | 119 | 358 | 10 |
| _emit_expr | `projects/ritz/ritz0/emitter/exprs.py:18` | 104 | 193 | 6 |
| _emit_method_call | `projects/ritz/ritz0/emitter_llvmlite.py:9752` | 97 | 213 | 6 |
| _emit_call_inner | `projects/ritz/ritz0/emitter_llvmlite.py:8342` | 93 | 215 | 10 |
| _emit_stmt | `projects/ritz/ritz0/emitter/stmts.py:33` | 91 | 273 | 10 |
| _emit_index | `projects/ritz/ritz0/emitter_llvmlite.py:6238` | 78 | 195 | 7 |
| _types_compatible | `projects/ritz/ritz0/type_checker.py:892` | 78 | 83 | 6 |
| _emit_call | `projects/ritz/ritz0/emitter/calls.py:17` | 67 | 152 | 5 |
| _convert_type | `projects/ritz/ritz0/emitter_llvmlite.py:10278` | 67 | 118 | 6 |
| _infer_ritz_type | `projects/ritz/ritz0/emitter_llvmlite.py:1093` | 63 | 114 | 7 |
| _emit_field_access | `projects/ritz/ritz0/emitter_llvmlite.py:8090` | 57 | 141 | 6 |
| evaluate | `projects/ritz/ritz0/const_eval.py:45` | 48 | 94 | 4 |
| _lex_operator | `projects/ritz/ritz0/lexer.py:441` | 45 | 103 | 3 |
| parse_primary | `projects/ritz/ritz0/parser.py:923` | 45 | 134 | 6 |
| _infer_type | `projects/ritz/ritz0/type_checker.py:317` | 44 | 100 | 4 |
| _emit_enum_match | `projects/ritz/ritz0/emitter_llvmlite.py:11168` | 43 | 111 | 12 |
| _emit_integer_match | `projects/ritz/ritz0/emitter_llvmlite.py:11383` | 43 | 88 | 5 |
| _ritz_type_to_llvm | `projects/ritz/ritz0/emitter_llvmlite.py:633` | 42 | 107 | 5 |
| _emit_for_iterable | `projects/ritz/ritz0/emitter_llvmlite.py:5588` | 42 | 148 | 7 |
| _register_item | `projects/ritz/ritz0/import_resolver.py:1161` | 42 | 101 | 8 |
| _lex_string | `projects/ritz/ritz0/lexer.py:161` | 42 | 109 | 8 |
| _emit_lvalue_addr | `projects/ritz/ritz0/emitter_llvmlite.py:7102` | 40 | 110 | 7 |

## Deepest nesting (top 25)

| fn | where | depth | SLOC |
|---|---|---|---|
| _emit_enum_match | `projects/ritz/ritz0/emitter_llvmlite.py:11168` | 12 | 111 |
| _emit_enum_variant_constructor | `projects/ritz/ritz0/emitter_llvmlite.py:2498` | 11 | 52 |
| _emit_enum_variant_constructor_for_type | `projects/ritz/ritz0/emitter_llvmlite.py:2659` | 11 | 44 |
| _register_method_instantiation | `projects/ritz/ritz0/monomorph.py:607` | 11 | 31 |
| _emit_stmt_inner | `projects/ritz/ritz0/emitter_llvmlite.py:4247` | 10 | 358 |
| _emit_stmt | `projects/ritz/ritz0/emitter/stmts.py:33` | 10 | 273 |
| _emit_call_inner | `projects/ritz/ritz0/emitter_llvmlite.py:8342` | 10 | 215 |
| _register_items_from_metadata | `projects/ritz/ritz0/import_resolver.py:983` | 10 | 150 |
| _specialize_enum | `projects/ritz/ritz0/monomorph.py:912` | 10 | 18 |
| _rewrite_enum | `projects/ritz/ritz0/monomorph.py:1242` | 10 | 15 |
| _process_import | `projects/ritz/ritz0/import_resolver.py:804` | 9 | 64 |
| parse_enum | `projects/ritz/ritz0/parser.py:1993` | 9 | 64 |
| _emit_struct_lit_into | `projects/ritz/ritz0/emitter_llvmlite.py:8034` | 9 | 39 |
| convert_postfix_expr | `projects/ritz/ritz0/parser_adapter.py:1013` | 9 | 36 |
| _lex_string | `projects/ritz/ritz0/lexer.py:161` | 8 | 109 |
| _register_item | `projects/ritz/ritz0/import_resolver.py:1161` | 8 | 101 |
| parse_postfix | `projects/ritz/ritz0/parser.py:786` | 8 | 97 |
| _check_expr | `projects/ritz/ritz0/move_checker.py:424` | 8 | 95 |
| _infer_value_type | `projects/ritz/ritz0/monomorph.py:548` | 8 | 45 |
| _emit_array_fill_to_alloca | `projects/ritz/ritz0/emitter/literals.py:373` | 8 | 40 |
| _emit_array_fill_to_alloca | `projects/ritz/ritz0/emitter_llvmlite.py:6891` | 8 | 40 |
| _try_emit_builtin_span_method | `projects/ritz/ritz0/emitter_llvmlite.py:9719` | 8 | 28 |
| _specialize_function_for_impl | `projects/ritz/ritz0/monomorph.py:993` | 8 | 25 |
| _rewrite_struct | `projects/ritz/ritz0/monomorph.py:1223` | 8 | 15 |
| _register_ufcs_instantiation | `projects/ritz/ritz0/monomorph.py:658` | 8 | 12 |

## Distribution

- functions > 100 SLOC: 36 (3.7%); > 300 SLOC: 3 (0.3%)
- CC > 20: 85 (8.8%); CC > 50: 14 (1.4%)
- nesting depth >= 6: 102 (10.5%)

## Files by size

| file | lines | SLOC | fns | dup-window lines |
|---|---|---|---|---|
| `projects/ritz/ritz0/emitter_llvmlite.py` | 12432 | 8727 | 256 | 5436 |
| `projects/ritz/ritz0/parser_gen.py` | 3170 | 2355 | 93 | 1194 |
| `projects/ritz/ritz0/parser.py` | 2428 | 1760 | 70 | 162 |
| `projects/ritz/ritz0/import_resolver.py` | 1506 | 1145 | 39 | 72 |
| `projects/ritz/ritz0/monomorph.py` | 1483 | 1134 | 44 | 60 |
| `projects/ritz/ritz0/parser_adapter.py` | 1462 | 1126 | 66 | 54 |
| `projects/ritz/ritz0/emitter/exprs.py` | 1407 | 954 | 17 | 1200 |
| `projects/ritz/ritz0/emitter/calls.py` | 1307 | 902 | 8 | 1608 |
| `projects/ritz/ritz0/emitter/stmts.py` | 1231 | 861 | 15 | 942 |
| `projects/ritz/ritz0/type_checker.py` | 1079 | 789 | 38 | 60 |
| `projects/ritz/ritz0/ritz_ast.py` | 1082 | 771 | 27 | 24 |
| `projects/ritz/ritz0/async_transform_v2.py` | 744 | 555 | 28 | 186 |
| `projects/ritz/ritz0/lexer.py` | 666 | 532 | 17 | 108 |
| `projects/ritz/ritz0/async_transform.py` | 680 | 525 | 23 | 198 |
| `projects/ritz/ritz0/emitter/patterns.py` | 820 | 504 | 14 | 660 |
| `projects/ritz/ritz0/move_checker.py` | 642 | 448 | 19 | 60 |
| `projects/ritz/ritz0/emitter/fn_cache.py` | 620 | 446 | 19 | 24 |
| `projects/ritz/ritz0/symbol_table.py` | 539 | 430 | 29 | 0 |
| `projects/ritz/ritz0/metadata.py` | 503 | 381 | 16 | 24 |
| `projects/ritz/ritz0/ast_builder.py` | 538 | 380 | 65 | 0 |
| `projects/ritz/ritz0/emitter/literals.py` | 571 | 360 | 16 | 480 |
| `projects/ritz/ritz0/ritz0.py` | 491 | 344 | 5 | 12 |
| `projects/ritz/ritz0/const_eval.py` | 403 | 329 | 17 | 0 |
| `projects/ritz/ritz0/name_resolver.py` | 416 | 316 | 18 | 0 |
| `projects/ritz/ritz0/tokens.py` | 210 | 171 | 2 | 0 |

## String / C-idiom smell counts per file

| file | bare_except | subprocess_shell_true | global_stmt | total |
|---|---|---|---|---|
| `projects/ritz/ritz0/emitter_llvmlite.py` | 0 | 0 | 2 | 2 |
| **total** | 0 | 0 | 2 | 2 |

## Duplicated 6-line windows (top 25 clusters by occurrences)

- **20×** `if result_1 is None:` — `projects/ritz/ritz0/parser_gen.py:627`, `projects/ritz/ritz0/parser_gen.py:639`, `projects/ritz/ritz0/parser_gen.py:651`, `projects/ritz/ritz0/parser_gen.py:663`, `projects/ritz/ritz0/parser_gen.py:675`, `projects/ritz/ritz0/parser_gen.py:687`, `projects/ritz/ritz0/parser_gen.py:699`, `projects/ritz/ritz0/parser_gen.py:1650` (+12 more)
- **20×** `raise ParseError("expected struct_def", self._peek())` — `projects/ritz/ritz0/parser_gen.py:628`, `projects/ritz/ritz0/parser_gen.py:640`, `projects/ritz/ritz0/parser_gen.py:652`, `projects/ritz/ritz0/parser_gen.py:664`, `projects/ritz/ritz0/parser_gen.py:676`, `projects/ritz/ritz0/parser_gen.py:688`, `projects/ritz/ritz0/parser_gen.py:700`, `projects/ritz/ritz0/parser_gen.py:1651` (+12 more)
- **11×** `if input_type == v4i32:` — `projects/ritz/ritz0/emitter/calls.py:698`, `projects/ritz/ritz0/emitter/calls.py:727`, `projects/ritz/ritz0/emitter/calls.py:756`, `projects/ritz/ritz0/emitter/calls.py:785`, `projects/ritz/ritz0/emitter/calls.py:812`, `projects/ritz/ritz0/emitter_llvmlite.py:9135`, `projects/ritz/ritz0/emitter_llvmlite.py:9164`, `projects/ritz/ritz0/emitter_llvmlite.py:9193` (+3 more)
- **10×** `key_i64 = key` — `projects/ritz/ritz0/emitter/calls.py:686`, `projects/ritz/ritz0/emitter/calls.py:716`, `projects/ritz/ritz0/emitter/calls.py:745`, `projects/ritz/ritz0/emitter/calls.py:774`, `projects/ritz/ritz0/emitter/calls.py:801`, `projects/ritz/ritz0/emitter_llvmlite.py:9123`, `projects/ritz/ritz0/emitter_llvmlite.py:9153`, `projects/ritz/ritz0/emitter_llvmlite.py:9182` (+2 more)
- **8×** `elif fname == 'aesenc':` — `projects/ritz/ritz0/emitter/calls.py:670`, `projects/ritz/ritz0/emitter/calls.py:702`, `projects/ritz/ritz0/emitter/calls.py:731`, `projects/ritz/ritz0/emitter/calls.py:760`, `projects/ritz/ritz0/emitter_llvmlite.py:9107`, `projects/ritz/ritz0/emitter_llvmlite.py:9139`, `projects/ritz/ritz0/emitter_llvmlite.py:9168`, `projects/ritz/ritz0/emitter_llvmlite.py:9197`
- **8×** `if len(args) != 2:` — `projects/ritz/ritz0/emitter/calls.py:674`, `projects/ritz/ritz0/emitter/calls.py:705`, `projects/ritz/ritz0/emitter/calls.py:734`, `projects/ritz/ritz0/emitter/calls.py:763`, `projects/ritz/ritz0/emitter_llvmlite.py:9111`, `projects/ritz/ritz0/emitter_llvmlite.py:9142`, `projects/ritz/ritz0/emitter_llvmlite.py:9171`, `projects/ritz/ritz0/emitter_llvmlite.py:9200`
- **8×** `state = self._emit_expr(args[0])` — `projects/ritz/ritz0/emitter/calls.py:676`, `projects/ritz/ritz0/emitter/calls.py:707`, `projects/ritz/ritz0/emitter/calls.py:736`, `projects/ritz/ritz0/emitter/calls.py:765`, `projects/ritz/ritz0/emitter_llvmlite.py:9113`, `projects/ritz/ritz0/emitter_llvmlite.py:9144`, `projects/ritz/ritz0/emitter_llvmlite.py:9173`, `projects/ritz/ritz0/emitter_llvmlite.py:9202`
- **8×** `key = self._emit_expr(args[1])` — `projects/ritz/ritz0/emitter/calls.py:677`, `projects/ritz/ritz0/emitter/calls.py:708`, `projects/ritz/ritz0/emitter/calls.py:737`, `projects/ritz/ritz0/emitter/calls.py:766`, `projects/ritz/ritz0/emitter_llvmlite.py:9114`, `projects/ritz/ritz0/emitter_llvmlite.py:9145`, `projects/ritz/ritz0/emitter_llvmlite.py:9174`, `projects/ritz/ritz0/emitter_llvmlite.py:9203`
- **8×** `input_type = state.type` — `projects/ritz/ritz0/emitter/calls.py:680`, `projects/ritz/ritz0/emitter/calls.py:710`, `projects/ritz/ritz0/emitter/calls.py:739`, `projects/ritz/ritz0/emitter/calls.py:768`, `projects/ritz/ritz0/emitter_llvmlite.py:9117`, `projects/ritz/ritz0/emitter_llvmlite.py:9147`, `projects/ritz/ritz0/emitter_llvmlite.py:9176`, `projects/ritz/ritz0/emitter_llvmlite.py:9205`
- **8×** `key_i64 = self.builder.bitcast(key, v2i64)` — `projects/ritz/ritz0/emitter/calls.py:683`, `projects/ritz/ritz0/emitter/calls.py:713`, `projects/ritz/ritz0/emitter/calls.py:742`, `projects/ritz/ritz0/emitter/calls.py:771`, `projects/ritz/ritz0/emitter_llvmlite.py:9120`, `projects/ritz/ritz0/emitter_llvmlite.py:9150`, `projects/ritz/ritz0/emitter_llvmlite.py:9179`, `projects/ritz/ritz0/emitter_llvmlite.py:9208`
- **8×** `elif input_type == v2i64:` — `projects/ritz/ritz0/emitter/calls.py:684`, `projects/ritz/ritz0/emitter/calls.py:714`, `projects/ritz/ritz0/emitter/calls.py:743`, `projects/ritz/ritz0/emitter/calls.py:772`, `projects/ritz/ritz0/emitter_llvmlite.py:9121`, `projects/ritz/ritz0/emitter_llvmlite.py:9151`, `projects/ritz/ritz0/emitter_llvmlite.py:9180`, `projects/ritz/ritz0/emitter_llvmlite.py:9209`
- **8×** `state_i64 = state` — `projects/ritz/ritz0/emitter/calls.py:685`, `projects/ritz/ritz0/emitter/calls.py:715`, `projects/ritz/ritz0/emitter/calls.py:744`, `projects/ritz/ritz0/emitter/calls.py:773`, `projects/ritz/ritz0/emitter_llvmlite.py:9122`, `projects/ritz/ritz0/emitter_llvmlite.py:9152`, `projects/ritz/ritz0/emitter_llvmlite.py:9181`, `projects/ritz/ritz0/emitter_llvmlite.py:9210`
- **8×** `intrinsic_name = 'llvm.x86.aesni.aesenc'` — `projects/ritz/ritz0/emitter/calls.py:690`, `projects/ritz/ritz0/emitter/calls.py:720`, `projects/ritz/ritz0/emitter/calls.py:749`, `projects/ritz/ritz0/emitter/calls.py:778`, `projects/ritz/ritz0/emitter_llvmlite.py:9127`, `projects/ritz/ritz0/emitter_llvmlite.py:9157`, `projects/ritz/ritz0/emitter_llvmlite.py:9186`, `projects/ritz/ritz0/emitter_llvmlite.py:9215`
- **8×** `if intrinsic_name in self.module.globals:` — `projects/ritz/ritz0/emitter/calls.py:691`, `projects/ritz/ritz0/emitter/calls.py:721`, `projects/ritz/ritz0/emitter/calls.py:750`, `projects/ritz/ritz0/emitter/calls.py:779`, `projects/ritz/ritz0/emitter_llvmlite.py:9128`, `projects/ritz/ritz0/emitter_llvmlite.py:9158`, `projects/ritz/ritz0/emitter_llvmlite.py:9187`, `projects/ritz/ritz0/emitter_llvmlite.py:9216`
- **8×** `intrinsic = self.module.globals[intrinsic_name]` — `projects/ritz/ritz0/emitter/calls.py:692`, `projects/ritz/ritz0/emitter/calls.py:722`, `projects/ritz/ritz0/emitter/calls.py:751`, `projects/ritz/ritz0/emitter/calls.py:780`, `projects/ritz/ritz0/emitter_llvmlite.py:9129`, `projects/ritz/ritz0/emitter_llvmlite.py:9159`, `projects/ritz/ritz0/emitter_llvmlite.py:9188`, `projects/ritz/ritz0/emitter_llvmlite.py:9217`
- **8×** `intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)` — `projects/ritz/ritz0/emitter/calls.py:695`, `projects/ritz/ritz0/emitter/calls.py:725`, `projects/ritz/ritz0/emitter/calls.py:754`, `projects/ritz/ritz0/emitter/calls.py:783`, `projects/ritz/ritz0/emitter_llvmlite.py:9132`, `projects/ritz/ritz0/emitter_llvmlite.py:9162`, `projects/ritz/ritz0/emitter_llvmlite.py:9191`, `projects/ritz/ritz0/emitter_llvmlite.py:9220`
- **8×** `result = self.builder.call(intrinsic, [state_i64, key_i64])` — `projects/ritz/ritz0/emitter/calls.py:696`, `projects/ritz/ritz0/emitter/calls.py:726`, `projects/ritz/ritz0/emitter/calls.py:755`, `projects/ritz/ritz0/emitter/calls.py:784`, `projects/ritz/ritz0/emitter_llvmlite.py:9133`, `projects/ritz/ritz0/emitter_llvmlite.py:9163`, `projects/ritz/ritz0/emitter_llvmlite.py:9192`, `projects/ritz/ritz0/emitter_llvmlite.py:9221`
- **8×** `return self.builder.icmp_signed('!=', left, right)` — `projects/ritz/ritz0/emitter/exprs.py:197`, `projects/ritz/ritz0/emitter/exprs.py:204`, `projects/ritz/ritz0/emitter/exprs.py:210`, `projects/ritz/ritz0/emitter/exprs.py:216`, `projects/ritz/ritz0/emitter_llvmlite.py:6110`, `projects/ritz/ritz0/emitter_llvmlite.py:6117`, `projects/ritz/ritz0/emitter_llvmlite.py:6123`, `projects/ritz/ritz0/emitter_llvmlite.py:6129`
- **7×** `if result_2 is None:` — `projects/ritz/ritz0/parser_gen.py:615`, `projects/ritz/ritz0/parser_gen.py:2651`, `projects/ritz/ritz0/parser_gen.py:2664`, `projects/ritz/ritz0/parser_gen.py:2677`, `projects/ritz/ritz0/parser_gen.py:2690`, `projects/ritz/ritz0/parser_gen.py:2703`, `projects/ritz/ritz0/parser_gen.py:2716`
- **7×** `raise ParseError("expected fn_def", self._peek())` — `projects/ritz/ritz0/parser_gen.py:616`, `projects/ritz/ritz0/parser_gen.py:2652`, `projects/ritz/ritz0/parser_gen.py:2665`, `projects/ritz/ritz0/parser_gen.py:2678`, `projects/ritz/ritz0/parser_gen.py:2691`, `projects/ritz/ritz0/parser_gen.py:2704`, `projects/ritz/ritz0/parser_gen.py:2717`
- **7×** `if result_3 is None:` — `projects/ritz/ritz0/parser_gen.py:964`, `projects/ritz/ritz0/parser_gen.py:2074`, `projects/ritz/ritz0/parser_gen.py:2196`, `projects/ritz/ritz0/parser_gen.py:2213`, `projects/ritz/ritz0/parser_gen.py:2230`, `projects/ritz/ritz0/parser_gen.py:2247`, `projects/ritz/ritz0/parser_gen.py:2264`
- **6×** `return self.builder.bitcast(result, v4i32)` — `projects/ritz/ritz0/emitter/calls.py:699`, `projects/ritz/ritz0/emitter/calls.py:728`, `projects/ritz/ritz0/emitter/calls.py:757`, `projects/ritz/ritz0/emitter_llvmlite.py:9136`, `projects/ritz/ritz0/emitter_llvmlite.py:9165`, `projects/ritz/ritz0/emitter_llvmlite.py:9194`
- **6×** `return self.builder.fcmp_ordered('<', left, right)` — `projects/ritz/ritz0/emitter/exprs.py:200`, `projects/ritz/ritz0/emitter/exprs.py:207`, `projects/ritz/ritz0/emitter/exprs.py:213`, `projects/ritz/ritz0/emitter_llvmlite.py:6113`, `projects/ritz/ritz0/emitter_llvmlite.py:6120`, `projects/ritz/ritz0/emitter_llvmlite.py:6126`
- **6×** `if result_1 is None:` — `projects/ritz/ritz0/parser_gen.py:711`, `projects/ritz/ritz0/parser_gen.py:1610`, `projects/ritz/ritz0/parser_gen.py:1782`, `projects/ritz/ritz0/parser_gen.py:2353`, `projects/ritz/ritz0/parser_gen.py:2728`, `projects/ritz/ritz0/parser_gen.py:3035`
- **6×** `result_3 = self.parse_expr()` — `projects/ritz/ritz0/parser_gen.py:2073`, `projects/ritz/ritz0/parser_gen.py:2195`, `projects/ritz/ritz0/parser_gen.py:2212`, `projects/ritz/ritz0/parser_gen.py:2229`, `projects/ritz/ritz0/parser_gen.py:2246`, `projects/ritz/ritz0/parser_gen.py:2263`

Total duplicate clusters: 884
