# ritz-metrics: 23 files, 25838 SLOC, 763 functions

## Longest functions (top 30)

| fn | where | SLOC | CC | depth |
|---|---|---|---|---|
| emit_expr_index | `projects/ritz/ritz1/src/emitter_expr_access.ritz:279` | 885 | 299 | 6 |
| emit_expr_call | `projects/ritz/ritz1/src/emitter_expr_call.ritz:1423` | 854 | 278 | 18 |
| emit_stmt | `projects/ritz/ritz1/src/emitter_stmt.ritz:1941` | 757 | 124 | 7 |
| parse_assign_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:4544` | 683 | 226 | 3 |
| emit_assign | `projects/ritz/ritz1/src/emitter_stmt.ritz:711` | 464 | 103 | 7 |
| emit_var_decl | `projects/ritz/ritz1/src/emitter_stmt.ritz:24` | 452 | 217 | 11 |
| emit_expr_method | `projects/ritz/ritz1/src/emitter_expr_call.ritz:2855` | 426 | 157 | 10 |
| parse_primary_expr | `projects/ritz/ritz1/src/parser_gen.ritz:6776` | 408 | 111 | 3 |
| parse_impl_block | `projects/ritz/ritz1/src/parser_gen.ritz:7491` | 364 | 116 | 3 |
| try_emit_ufcs_method | `projects/ritz/ritz1/src/emitter_expr_call.ritz:244` | 323 | 83 | 6 |
| emit_expr_binary | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:11` | 312 | 81 | 4 |
| parse_type_spec | `projects/ritz/ritz1/src/parser_gen.ritz:2015` | 303 | 86 | 3 |
| emit_lvalue_ptr | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:509` | 299 | 87 | 9 |
| emit_member_ptr | `projects/ritz/ritz1/src/emitter_expr.ritz:196` | 293 | 93 | 8 |
| emit_expr | `projects/ritz/ritz1/src/emitter_expr.ritz:816` | 289 | 48 | 5 |
| parse_let_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:3196` | 254 | 84 | 3 |
| parse_postfix_op | `projects/ritz/ritz1/src/parser_gen.ritz:6404` | 252 | 75 | 3 |
| lexer_next | `projects/ritz/ritz1/src/lexer_nfa.ritz:387` | 240 | 98 | 14 |
| emit_impl_method | `projects/ritz/ritz1/src/emitter.ritz:653` | 238 | 59 | 6 |
| parse_var_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:3552` | 229 | 76 | 3 |
| emit_for_iterable | `projects/ritz/ritz1/src/emitter_stmt.ritz:1520` | 226 | 23 | 9 |
| emit_fn | `projects/ritz/ritz1/src/emitter.ritz:354` | 225 | 48 | 6 |
| emit_expr_ident | `projects/ritz/ritz1/src/emitter_expr_access.ritz:16` | 183 | 35 | 7 |
| emit_array_fill_into | `projects/ritz/ritz1/src/emitter_expr.ritz:1278` | 167 | 26 | 3 |
| parse_global_var_def | `projects/ritz/ritz1/src/parser_gen.ritz:1788` | 165 | 54 | 3 |
| parse_item | `projects/ritz/ritz1/src/parser_gen.ritz:236` | 148 | 50 | 4 |
| emit_expr_unary | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:905` | 146 | 20 | 4 |
| emit_return | `projects/ritz/ritz1/src/emitter_stmt.ritz:1312` | 138 | 23 | 5 |
| emit_expr_member | `projects/ritz/ritz1/src/emitter_expr_access.ritz:1303` | 133 | 19 | 6 |
| parse_param | `projects/ritz/ritz1/src/parser_gen.ritz:1181` | 125 | 38 | 3 |

## Highest cyclomatic complexity (top 30)

| fn | where | CC | SLOC | depth |
|---|---|---|---|---|
| emit_expr_index | `projects/ritz/ritz1/src/emitter_expr_access.ritz:279` | 299 | 885 | 6 |
| emit_expr_call | `projects/ritz/ritz1/src/emitter_expr_call.ritz:1423` | 278 | 854 | 18 |
| parse_assign_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:4544` | 226 | 683 | 3 |
| emit_var_decl | `projects/ritz/ritz1/src/emitter_stmt.ritz:24` | 217 | 452 | 11 |
| emit_expr_method | `projects/ritz/ritz1/src/emitter_expr_call.ritz:2855` | 157 | 426 | 10 |
| emit_stmt | `projects/ritz/ritz1/src/emitter_stmt.ritz:1941` | 124 | 757 | 7 |
| parse_impl_block | `projects/ritz/ritz1/src/parser_gen.ritz:7491` | 116 | 364 | 3 |
| parse_primary_expr | `projects/ritz/ritz1/src/parser_gen.ritz:6776` | 111 | 408 | 3 |
| emit_assign | `projects/ritz/ritz1/src/emitter_stmt.ritz:711` | 103 | 464 | 7 |
| lexer_next | `projects/ritz/ritz1/src/lexer_nfa.ritz:387` | 98 | 240 | 14 |
| emit_member_ptr | `projects/ritz/ritz1/src/emitter_expr.ritz:196` | 93 | 293 | 8 |
| emit_lvalue_ptr | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:509` | 87 | 299 | 9 |
| parse_type_spec | `projects/ritz/ritz1/src/parser_gen.ritz:2015` | 86 | 303 | 3 |
| parse_let_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:3196` | 84 | 254 | 3 |
| try_emit_ufcs_method | `projects/ritz/ritz1/src/emitter_expr_call.ritz:244` | 83 | 323 | 6 |
| emit_expr_binary | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:11` | 81 | 312 | 4 |
| parse_var_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:3552` | 76 | 229 | 3 |
| parse_postfix_op | `projects/ritz/ritz1/src/parser_gen.ritz:6404` | 75 | 252 | 3 |
| emit_impl_method | `projects/ritz/ritz1/src/emitter.ritz:653` | 59 | 238 | 6 |
| parse_global_var_def | `projects/ritz/ritz1/src/parser_gen.ritz:1788` | 54 | 165 | 3 |
| get_expr_type | `projects/ritz/ritz1/src/emitter_core.ritz:2363` | 53 | 111 | 7 |
| parse_item | `projects/ritz/ritz1/src/parser_gen.ritz:236` | 50 | 148 | 4 |
| emit_fn | `projects/ritz/ritz1/src/emitter.ritz:354` | 48 | 225 | 6 |
| emit_expr | `projects/ritz/ritz1/src/emitter_expr.ritz:816` | 48 | 289 | 5 |
| read_sig_file | `projects/ritz/ritz1/src/fn_cache.ritz:497` | 45 | 82 | 7 |
| collect_from_stmt | `projects/ritz/ritz1/src/monomorph.ritz:626` | 43 | 80 | 8 |
| narrow_const_value | `projects/ritz/ritz1/src/narrowing.ritz:330` | 43 | 88 | 4 |
| parse_for_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:3993` | 40 | 118 | 3 |
| try_emit_enum_is_ok | `projects/ritz/ritz1/src/emitter_expr.ritz:593` | 39 | 59 | 3 |
| parse_param | `projects/ritz/ritz1/src/parser_gen.ritz:1181` | 38 | 125 | 3 |

## Deepest nesting (top 30)

| fn | where | depth | SLOC |
|---|---|---|---|
| emit_expr_call | `projects/ritz/ritz1/src/emitter_expr_call.ritz:1423` | 18 | 854 |
| lexer_next | `projects/ritz/ritz1/src/lexer_nfa.ritz:387` | 14 | 240 |
| emit_var_decl | `projects/ritz/ritz1/src/emitter_stmt.ritz:24` | 11 | 452 |
| try_emit_enum_unwrap | `projects/ritz/ritz1/src/emitter_expr_call.ritz:2490` | 11 | 106 |
| emit_expr_method | `projects/ritz/ritz1/src/emitter_expr_call.ritz:2855` | 10 | 426 |
| emit_lvalue_ptr | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:509` | 9 | 299 |
| emit_for_iterable | `projects/ritz/ritz1/src/emitter_stmt.ritz:1520` | 9 | 226 |
| is_tagged_enum_type | `projects/ritz/ritz1/src/emitter_core.ritz:1136` | 9 | 19 |
| emit_member_ptr | `projects/ritz/ritz1/src/emitter_expr.ritz:196` | 8 | 293 |
| collect_from_stmt | `projects/ritz/ritz1/src/monomorph.ritz:626` | 8 | 80 |
| resolve_expr_struct_name | `projects/ritz/ritz1/src/emitter_core.ritz:1719` | 8 | 68 |
| is_local_function | `projects/ritz/ritz1/src/emitter.ritz:1022` | 8 | 42 |
| enum_variant_index | `projects/ritz/ritz1/src/ast_helpers.ritz:3080` | 8 | 36 |
| emit_stmt | `projects/ritz/ritz1/src/emitter_stmt.ritz:1941` | 7 | 757 |
| emit_assign | `projects/ritz/ritz1/src/emitter_stmt.ritz:711` | 7 | 464 |
| emit_expr_ident | `projects/ritz/ritz1/src/emitter_expr_access.ritz:16` | 7 | 183 |
| get_expr_type | `projects/ritz/ritz1/src/emitter_core.ritz:2363` | 7 | 111 |
| read_sig_file | `projects/ritz/ritz1/src/fn_cache.ritz:497` | 7 | 82 |
| struct_deps_satisfied | `projects/ritz/ritz1/src/emitter.ritz:1463` | 7 | 16 |
| emit_expr_index | `projects/ritz/ritz1/src/emitter_expr_access.ritz:279` | 6 | 885 |
| try_emit_ufcs_method | `projects/ritz/ritz1/src/emitter_expr_call.ritz:244` | 6 | 323 |
| emit_impl_method | `projects/ritz/ritz1/src/emitter.ritz:653` | 6 | 238 |
| emit_fn | `projects/ritz/ritz1/src/emitter.ritz:354` | 6 | 225 |
| emit_expr_member | `projects/ritz/ritz1/src/emitter_expr_access.ritz:1303` | 6 | 133 |
| emit_variant_struct | `projects/ritz/ritz1/src/emitter_expr_call.ritz:765` | 6 | 119 |
| try_open_import | `projects/ritz/ritz1/src/main.ritz:315` | 6 | 79 |
| emit_match_arm_body | `projects/ritz/ritz1/src/emitter_match.ritz:285` | 6 | 70 |
| emit_match_arm | `projects/ritz/ritz1/src/emitter_match.ritz:383` | 6 | 61 |
| specialize_fn_one_param | `projects/ritz/ritz1/src/monomorph.ritz:1022` | 6 | 55 |
| resolve_scrutinee_enum | `projects/ritz/ritz1/src/emitter_match.ritz:463` | 6 | 41 |

## Distribution

- functions > 100 SLOC: 38 (5.0%); > 300 SLOC: 12 (1.6%)
- CC > 20: 76 (10.0%); CC > 50: 21 (2.8%)
- nesting depth >= 6: 34 (4.5%)

## Files by size

| file | lines | SLOC | fns | dup-window lines |
|---|---|---|---|---|
| `projects/ritz/ritz1/src/parser_gen.ritz` | 7913 | 6357 | 108 | 2154 |
| `projects/ritz/ritz1/src/emitter_expr_call.ritz` | 3426 | 2691 | 37 | 888 |
| `projects/ritz/ritz1/src/ast_helpers.ritz` | 3215 | 2217 | 176 | 420 |
| `projects/ritz/ritz1/src/emitter_stmt.ritz` | 2956 | 2205 | 10 | 1188 |
| `projects/ritz/ritz1/src/emitter.ritz` | 2635 | 1852 | 57 | 342 |
| `projects/ritz/ritz1/src/emitter_core.ritz` | 2641 | 1674 | 111 | 120 |
| `projects/ritz/ritz1/src/monomorph.ritz` | 1985 | 1379 | 73 | 36 |
| `projects/ritz/ritz1/src/emitter_expr.ritz` | 1760 | 1348 | 15 | 372 |
| `projects/ritz/ritz1/src/emitter_expr_access.ritz` | 1465 | 1243 | 6 | 630 |
| `projects/ritz/ritz1/src/emitter_expr_arith.ritz` | 1070 | 824 | 5 | 204 |
| `projects/ritz/ritz1/src/fn_cache.ritz` | 920 | 608 | 29 | 48 |
| `projects/ritz/ritz1/src/main.ritz` | 832 | 529 | 24 | 24 |
| `projects/ritz/ritz1/src/emitter_match.ritz` | 714 | 506 | 16 | 168 |
| `projects/ritz/ritz1/src/lexer_nfa.ritz` | 722 | 450 | 14 | 60 |
| `projects/ritz/ritz1/src/narrowing.ritz` | 535 | 415 | 22 | 0 |
| `projects/ritz/ritz1/src/emitter_print.ritz` | 437 | 356 | 11 | 90 |
| `projects/ritz/ritz1/src/ast.ritz` | 541 | 319 | 0 | 0 |
| `projects/ritz/ritz1/src/nfa.ritz` | 417 | 262 | 23 | 12 |
| `projects/ritz/ritz1/src/regex.ritz` | 270 | 169 | 12 | 0 |
| `projects/ritz/ritz1/src/tokens_gen.ritz` | 148 | 120 | 1 | 0 |
| `projects/ritz/ritz1/src/ll_copy_scan.ritz` | 143 | 107 | 8 | 0 |
| `projects/ritz/ritz1/src/lexer_setup_gen.ritz` | 120 | 105 | 1 | 0 |
| `projects/ritz/ritz1/src/interp.ritz` | 153 | 102 | 4 | 12 |

## String / C-idiom smell counts per file

| file | ptr_len_param_pair | fixed_u8_buffer | strlen_call | memcpy_call | memcmp_or_streq_call | manual_byte_copy | manual_byte_compare | char_code_compare | cstr_literal | malloc_cast | malloc_magic_size | i32_as_bool | total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `projects/ritz/ritz1/src/emitter_expr_call.ritz` | 14 | 5 | 0 | 0 | 52 | 19 | 0 | 0 | 758 | 0 | 0 | 87 | 935 |
| `projects/ritz/ritz1/src/emitter_stmt.ritz` | 2 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 658 | 0 | 0 | 32 | 698 |
| `projects/ritz/ritz1/src/emitter.ritz` | 15 | 0 | 0 | 4 | 27 | 0 | 0 | 0 | 466 | 2 | 2 | 44 | 560 |
| `projects/ritz/ritz1/src/emitter_expr_access.ritz` | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 475 | 0 | 0 | 4 | 482 |
| `projects/ritz/ritz1/src/emitter_core.ritz` | 57 | 3 | 0 | 0 | 77 | 0 | 0 | 0 | 262 | 2 | 0 | 38 | 439 |
| `projects/ritz/ritz1/src/emitter_expr.ritz` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 398 | 0 | 0 | 16 | 415 |
| `projects/ritz/ritz1/src/emitter_expr_arith.ritz` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 269 | 0 | 0 | 10 | 279 |
| `projects/ritz/ritz1/src/monomorph.ritz` | 47 | 0 | 0 | 1 | 42 | 0 | 0 | 0 | 44 | 31 | 0 | 45 | 210 |
| `projects/ritz/ritz1/src/emitter_print.ritz` | 3 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 145 | 0 | 0 | 6 | 156 |
| `projects/ritz/ritz1/src/emitter_match.ritz` | 8 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 112 | 0 | 0 | 15 | 136 |
| `projects/ritz/ritz1/src/ast_helpers.ritz` | 65 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 26 | 7 | 0 | 30 | 128 |
| `projects/ritz/ritz1/src/fn_cache.ritz` | 9 | 5 | 3 | 6 | 1 | 0 | 0 | 0 | 39 | 3 | 1 | 14 | 81 |
| `projects/ritz/ritz1/src/narrowing.ritz` | 1 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 19 | 0 | 0 | 6 | 29 |
| `projects/ritz/ritz1/src/main.ritz` | 2 | 1 | 0 | 3 | 0 | 0 | 0 | 0 | 11 | 0 | 0 | 3 | 20 |
| `projects/ritz/ritz1/src/ll_copy_scan.ritz` | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 0 | 17 |
| `projects/ritz/ritz1/src/lexer_nfa.ritz` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 9 | 12 |
| `projects/ritz/ritz1/src/nfa.ritz` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 5 | 11 |
| `projects/ritz/ritz1/src/ast.ritz` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 9 | 10 |
| `projects/ritz/ritz1/src/interp.ritz` | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 10 |
| `projects/ritz/ritz1/src/regex.ritz` | 2 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 7 | 10 |
| `projects/ritz/ritz1/src/tokens_gen.ritz` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| **total** | 240 | 20 | 3 | 14 | 206 | 20 | 0 | 0 | 3700 | 45 | 3 | 389 | 4640 |

## Duplicated 6-line windows (top 30 clusters by occurrences)

- **33×** `emit_str(s, c"; Inline syscall implementations (weak_odr — linker merges duplica` — `projects/ritz/ritz1/src/emitter.ritz:1082`, `projects/ritz/ritz1/src/emitter.ritz:1088`, `projects/ritz/ritz1/src/emitter.ritz:1094`, `projects/ritz/ritz1/src/emitter.ritz:1101`, `projects/ritz/ritz1/src/emitter.ritz:1107`, `projects/ritz/ritz1/src/emitter.ritz:1113`, `projects/ritz/ritz1/src/emitter.ritz:1119`, `projects/ritz/ritz1/src/emitter.ritz:1125` (+25 more)
- **19×** `let trunc: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter.ritz:585`, `projects/ritz/ritz1/src/emitter.ritz:865`, `projects/ritz/ritz1/src/emitter_stmt.ritz:726`, `projects/ritz/ritz1/src/emitter_stmt.ritz:740`, `projects/ritz/ritz1/src/emitter_stmt.ritz:752`, `projects/ritz/ritz1/src/emitter_stmt.ritz:860`, `projects/ritz/ritz1/src/emitter_stmt.ritz:872`, `projects/ritz/ritz1/src/emitter_stmt.ritz:1076` (+11 more)
- **19×** `emit_str(s, c"  ")` — `projects/ritz/ritz1/src/emitter.ritz:586`, `projects/ritz/ritz1/src/emitter.ritz:866`, `projects/ritz/ritz1/src/emitter_stmt.ritz:727`, `projects/ritz/ritz1/src/emitter_stmt.ritz:741`, `projects/ritz/ritz1/src/emitter_stmt.ritz:753`, `projects/ritz/ritz1/src/emitter_stmt.ritz:861`, `projects/ritz/ritz1/src/emitter_stmt.ritz:873`, `projects/ritz/ritz1/src/emitter_stmt.ritz:1077` (+11 more)
- **19×** `emit_reg(s, trunc)` — `projects/ritz/ritz1/src/emitter.ritz:587`, `projects/ritz/ritz1/src/emitter.ritz:867`, `projects/ritz/ritz1/src/emitter_stmt.ritz:728`, `projects/ritz/ritz1/src/emitter_stmt.ritz:742`, `projects/ritz/ritz1/src/emitter_stmt.ritz:754`, `projects/ritz/ritz1/src/emitter_stmt.ritz:862`, `projects/ritz/ritz1/src/emitter_stmt.ritz:874`, `projects/ritz/ritz1/src/emitter_stmt.ritz:1078` (+11 more)
- **19×** `emit_str(s, c" = trunc i64 ")` — `projects/ritz/ritz1/src/emitter.ritz:588`, `projects/ritz/ritz1/src/emitter.ritz:868`, `projects/ritz/ritz1/src/emitter_stmt.ritz:729`, `projects/ritz/ritz1/src/emitter_stmt.ritz:743`, `projects/ritz/ritz1/src/emitter_stmt.ritz:755`, `projects/ritz/ritz1/src/emitter_stmt.ritz:863`, `projects/ritz/ritz1/src/emitter_stmt.ritz:875`, `projects/ritz/ritz1/src/emitter_stmt.ritz:1079` (+11 more)
- **13×** `let ext: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:984`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:992`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1000`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1008`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1016`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1024`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1392`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1400` (+5 more)
- **13×** `let ext: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_call.ritz:564`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:572`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:580`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:588`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:596`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:604`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:2352`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:2360` (+5 more)
- **12×** `emit_ir_error(s, c"variant constructor has no enum context: the call parameter i` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:32`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:773`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:973`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1018`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1065`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1096`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1145`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1197` (+4 more)
- **10×** `let ext: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:114`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:122`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:130`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:170`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:178`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:820`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:828`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:836` (+2 more)
- **10×** `emit_str(s, c"  ")` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:115`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:123`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:131`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:171`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:179`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:821`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:829`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:837` (+2 more)
- **9×** `let field_ptr: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr.ritz:35`, `projects/ritz/ritz1/src/emitter_expr.ritz:51`, `projects/ritz/ritz1/src/emitter_expr.ritz:223`, `projects/ritz/ritz1/src/emitter_expr.ritz:1569`, `projects/ritz/ritz1/src/emitter_expr.ritz:1618`, `projects/ritz/ritz1/src/emitter_expr_arith.ritz:818`, `projects/ritz/ritz1/src/emitter_expr_arith.ritz:833`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2495` (+1 more)
- **8×** `p.pos = start_pos` — `projects/ritz/ritz1/src/parser_gen.ritz:158`, `projects/ritz/ritz1/src/parser_gen.ritz:454`, `projects/ritz/ritz1/src/parser_gen.ritz:628`, `projects/ritz/ritz1/src/parser_gen.ritz:974`, `projects/ritz/ritz1/src/parser_gen.ritz:1370`, `projects/ritz/ritz1/src/parser_gen.ritz:1533`, `projects/ritz/ritz1/src/parser_gen.ritz:1803`, `projects/ritz/ritz1/src/parser_gen.ritz:4008`
- **7×** `let trunc: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_call.ritz:352`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:360`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:368`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1778`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1786`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1794`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1968`
- **7×** `p.pos = start_pos` — `projects/ritz/ritz1/src/parser_gen.ritz:1132`, `projects/ritz/ritz1/src/parser_gen.ritz:1716`, `projects/ritz/ritz1/src/parser_gen.ritz:2622`, `projects/ritz/ritz1/src/parser_gen.ritz:6711`, `projects/ritz/ritz1/src/parser_gen.ritz:6750`, `projects/ritz/ritz1/src/parser_gen.ritz:7363`, `projects/ritz/ritz1/src/parser_gen.ritz:7460`
- **6×** `let ext: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:599`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:607`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:615`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:623`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:631`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:639`
- **6×** `emit_str(s, c"  ")` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:600`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:608`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:616`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:624`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:632`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:640`
- **6×** `let ext: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:710`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:718`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:726`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:734`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:742`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:750`
- **6×** `let ext: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:1133`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1141`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1149`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1157`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1165`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1173`
- **6×** `if p.error == 0` — `projects/ritz/ritz1/src/parser_gen.ritz:159`, `projects/ritz/ritz1/src/parser_gen.ritz:455`, `projects/ritz/ritz1/src/parser_gen.ritz:629`, `projects/ritz/ritz1/src/parser_gen.ritz:1534`, `projects/ritz/ritz1/src/parser_gen.ritz:1804`, `projects/ritz/ritz1/src/parser_gen.ritz:4009`
- **6×** `result_a1_2 = p_current_token(p)` — `projects/ritz/ritz1/src/parser_gen.ritz:160`, `projects/ritz/ritz1/src/parser_gen.ritz:456`, `projects/ritz/ritz1/src/parser_gen.ritz:630`, `projects/ritz/ritz1/src/parser_gen.ritz:1535`, `projects/ritz/ritz1/src/parser_gen.ritz:1805`, `projects/ritz/ritz1/src/parser_gen.ritz:4010`
- **6×** `p.pos = start_pos` — `projects/ritz/ritz1/src/parser_gen.ritz:183`, `projects/ritz/ritz1/src/parser_gen.ritz:483`, `projects/ritz/ritz1/src/parser_gen.ritz:652`, `projects/ritz/ritz1/src/parser_gen.ritz:1566`, `projects/ritz/ritz1/src/parser_gen.ritz:4353`, `projects/ritz/ritz1/src/parser_gen.ritz:6452`
- **6×** `result_a2_1 = p_current_token(p)` — `projects/ritz/ritz1/src/parser_gen.ritz:495`, `projects/ritz/ritz1/src/parser_gen.ritz:663`, `projects/ritz/ritz1/src/parser_gen.ritz:752`, `projects/ritz/ritz1/src/parser_gen.ritz:1024`, `projects/ritz/ritz1/src/parser_gen.ritz:1416`, `projects/ritz/ritz1/src/parser_gen.ritz:1579`
- **6×** `p.pos = start_pos` — `projects/ritz/ritz1/src/parser_gen.ritz:503`, `projects/ritz/ritz1/src/parser_gen.ritz:671`, `projects/ritz/ritz1/src/parser_gen.ritz:1032`, `projects/ritz/ritz1/src/parser_gen.ritz:1424`, `projects/ritz/ritz1/src/parser_gen.ritz:1587`, `projects/ritz/ritz1/src/parser_gen.ritz:4372`
- **6×** `if p.error != 0` — `projects/ritz/ritz1/src/parser_gen.ritz:2643`, `projects/ritz/ritz1/src/parser_gen.ritz:2874`, `projects/ritz/ritz1/src/parser_gen.ritz:4207`, `projects/ritz/ritz1/src/parser_gen.ritz:4493`, `projects/ritz/ritz1/src/parser_gen.ritz:6732`, `projects/ritz/ritz1/src/parser_gen.ritz:6767`
- **5×** `stored = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr.ritz:1532`, `projects/ritz/ritz1/src/emitter_expr.ritz:1539`, `projects/ritz/ritz1/src/emitter_expr.ritz:1647`, `projects/ritz/ritz1/src/emitter_expr.ritz:1659`, `projects/ritz/ritz1/src/emitter_expr.ritz:1686`
- **5×** `emit_str(s, c", i64 0, i64 ")` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:462`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:794`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1200`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1244`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1284`
- **5×** `let result: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_call.ritz:996`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1177`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1216`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1309`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1397`
- **5×** `if e.args == null or e.args.next == null` — `projects/ritz/ritz1/src/emitter_expr_call.ritz:1017`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1064`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1095`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1251`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1324`
- **5×** `if p.error == 0` — `projects/ritz/ritz1/src/parser_gen.ritz:504`, `projects/ritz/ritz1/src/parser_gen.ritz:672`, `projects/ritz/ritz1/src/parser_gen.ritz:1588`, `projects/ritz/ritz1/src/parser_gen.ritz:4373`, `projects/ritz/ritz1/src/parser_gen.ritz:7597`
- **5×** `result_a1_1 = p_current_token(p)` — `projects/ritz/ritz1/src/parser_gen.ritz:871`, `projects/ritz/ritz1/src/parser_gen.ritz:1713`, `projects/ritz/ritz1/src/parser_gen.ritz:1981`, `projects/ritz/ritz1/src/parser_gen.ritz:2660`, `projects/ritz/ritz1/src/parser_gen.ritz:7457`

Total duplicate clusters: 400
