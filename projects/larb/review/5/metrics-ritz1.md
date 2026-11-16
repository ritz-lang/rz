# ritz-metrics: 41 files, 56636 SLOC, 2515 functions

## Longest functions (top 30)

| fn | where | SLOC | CC | depth |
|---|---|---|---|---|
| emit_stmt_inner | `projects/ritz/ritz1/src/emitter_stmt.ritz:5720` | 786 | 144 | 6 |
| emit_var_decl_at | `projects/ritz/ritz1/src/emitter_stmt.ritz:1233` | 764 | 339 | 11 |
| emit_expr_call | `projects/ritz/ritz1/src/emitter_expr_call.ritz:4199` | 762 | 241 | 18 |
| emit_expr_method | `projects/ritz/ritz1/src/emitter_expr_call.ritz:6123` | 721 | 268 | 10 |
| emit_expr_index | `projects/ritz/ritz1/src/emitter_expr_access.ritz:778` | 705 | 246 | 6 |
| parse_assign_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:6214` | 635 | 210 | 3 |
| parse_primary_expr | `projects/ritz/ritz1/src/parser_gen.ritz:8772` | 527 | 149 | 3 |
| emit_assign | `projects/ritz/ritz1/src/emitter_stmt.ritz:2540` | 524 | 138 | 6 |
| emit_member_ptr_at | `projects/ritz/ritz1/src/emitter_expr.ritz:475` | 417 | 153 | 8 |
| parse_type_spec | `projects/ritz/ritz1/src/parser_gen.ritz:2642` | 396 | 114 | 3 |
| parse_impl_block | `projects/ritz/ritz1/src/parser_gen.ritz:9648` | 364 | 116 | 3 |
| emit_lvalue_ptr | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:1557` | 354 | 81 | 9 |
| parse_let_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:4661` | 354 | 116 | 3 |
| emit_for_iterable | `projects/ritz/ritz1/src/emitter_stmt.ritz:3993` | 352 | 69 | 6 |
| emit_expr_binary | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:225` | 332 | 101 | 4 |
| emit_impl_method | `projects/ritz/ritz1/src/emitter.ritz:1125` | 297 | 67 | 6 |
| parse_postfix_op | `projects/ritz/ritz1/src/parser_gen.ritz:8345` | 297 | 89 | 3 |
| parse_global_var_def | `projects/ritz/ritz1/src/parser_gen.ritz:2269` | 296 | 96 | 3 |
| emit_fn | `projects/ritz/ritz1/src/emitter.ritz:748` | 291 | 64 | 6 |
| emit_expr | `projects/ritz/ritz1/src/emitter_expr.ritz:1605` | 284 | 62 | 4 |
| emit_expr_ident | `projects/ritz/ritz1/src/emitter_expr_access.ritz:59` | 256 | 58 | 6 |
| lexer_next_token | `projects/ritz/ritz1/src/lexer_nfa.ritz:660` | 240 | 105 | 14 |
| parse_var_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:5127` | 229 | 76 | 3 |
| parse_fn_def | `projects/ritz/ritz1/src/parser_gen.ritz:1137` | 225 | 66 | 3 |
| emit_ufcs_call | `projects/ritz/ritz1/src/emitter_expr_call.ritz:775` | 220 | 74 | 6 |
| emit_expr_unary | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:2038` | 201 | 33 | 4 |
| emit_array_fill_into | `projects/ritz/ritz1/src/emitter_expr.ritz:2192` | 195 | 42 | 4 |
| get_expr_type | `projects/ritz/ritz1/src/emitter_core.ritz:5861` | 190 | 103 | 7 |
| emit_match_arm_body | `projects/ritz/ritz1/src/emitter_match.ritz:684` | 178 | 73 | 7 |
| parse_param | `projects/ritz/ritz1/src/parser_gen.ritz:1492` | 177 | 54 | 3 |

## Highest cyclomatic complexity (top 30)

| fn | where | CC | SLOC | depth |
|---|---|---|---|---|
| emit_var_decl_at | `projects/ritz/ritz1/src/emitter_stmt.ritz:1233` | 339 | 764 | 11 |
| emit_expr_method | `projects/ritz/ritz1/src/emitter_expr_call.ritz:6123` | 268 | 721 | 10 |
| emit_expr_index | `projects/ritz/ritz1/src/emitter_expr_access.ritz:778` | 246 | 705 | 6 |
| emit_expr_call | `projects/ritz/ritz1/src/emitter_expr_call.ritz:4199` | 241 | 762 | 18 |
| parse_assign_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:6214` | 210 | 635 | 3 |
| emit_member_ptr_at | `projects/ritz/ritz1/src/emitter_expr.ritz:475` | 153 | 417 | 8 |
| parse_primary_expr | `projects/ritz/ritz1/src/parser_gen.ritz:8772` | 149 | 527 | 3 |
| emit_stmt_inner | `projects/ritz/ritz1/src/emitter_stmt.ritz:5720` | 144 | 786 | 6 |
| emit_assign | `projects/ritz/ritz1/src/emitter_stmt.ritz:2540` | 138 | 524 | 6 |
| parse_let_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:4661` | 116 | 354 | 3 |
| parse_impl_block | `projects/ritz/ritz1/src/parser_gen.ritz:9648` | 116 | 364 | 3 |
| parse_type_spec | `projects/ritz/ritz1/src/parser_gen.ritz:2642` | 114 | 396 | 3 |
| lexer_next_token | `projects/ritz/ritz1/src/lexer_nfa.ritz:660` | 105 | 240 | 14 |
| get_expr_type | `projects/ritz/ritz1/src/emitter_core.ritz:5861` | 103 | 190 | 7 |
| emit_expr_binary | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:225` | 101 | 332 | 4 |
| parse_global_var_def | `projects/ritz/ritz1/src/parser_gen.ritz:2269` | 96 | 296 | 3 |
| parse_postfix_op | `projects/ritz/ritz1/src/parser_gen.ritz:8345` | 89 | 297 | 3 |
| emit_lvalue_ptr | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:1557` | 81 | 354 | 9 |
| parse_var_stmt | `projects/ritz/ritz1/src/parser_gen.ritz:5127` | 76 | 229 | 3 |
| emit_ufcs_call | `projects/ritz/ritz1/src/emitter_expr_call.ritz:775` | 74 | 220 | 6 |
| emit_match_arm_body | `projects/ritz/ritz1/src/emitter_match.ritz:684` | 73 | 178 | 7 |
| emit_for_iterable | `projects/ritz/ritz1/src/emitter_stmt.ritz:3993` | 69 | 352 | 6 |
| emit_impl_method | `projects/ritz/ritz1/src/emitter.ritz:1125` | 67 | 297 | 6 |
| parse_fn_def | `projects/ritz/ritz1/src/parser_gen.ritz:1137` | 66 | 225 | 3 |
| emit_fn | `projects/ritz/ritz1/src/emitter.ritz:748` | 64 | 291 | 6 |
| emit_expr | `projects/ritz/ritz1/src/emitter_expr.ritz:1605` | 62 | 284 | 4 |
| collect_from_stmt | `projects/ritz/ritz1/src/monomorph.ritz:1160` | 61 | 105 | 8 |
| emit_expr_ident | `projects/ritz/ritz1/src/emitter_expr_access.ritz:59` | 58 | 256 | 6 |
| own_walk | `projects/ritz/ritz1/src/ownership.ritz:2523` | 55 | 107 | 5 |
| deref_pointee_struct_name | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:1107` | 54 | 68 | 4 |

## Deepest nesting (top 30)

| fn | where | depth | SLOC |
|---|---|---|---|
| emit_expr_call | `projects/ritz/ritz1/src/emitter_expr_call.ritz:4199` | 18 | 762 |
| lexer_next_token | `projects/ritz/ritz1/src/lexer_nfa.ritz:660` | 14 | 240 |
| emit_var_decl_at | `projects/ritz/ritz1/src/emitter_stmt.ritz:1233` | 11 | 764 |
| try_emit_enum_unwrap | `projects/ritz/ritz1/src/emitter_expr_call.ritz:5180` | 11 | 136 |
| emit_expr_method | `projects/ritz/ritz1/src/emitter_expr_call.ritz:6123` | 10 | 721 |
| emit_lvalue_ptr | `projects/ritz/ritz1/src/emitter_expr_arith.ritz:1557` | 9 | 354 |
| is_tagged_enum_type | `projects/ritz/ritz1/src/emitter_core.ritz:2287` | 9 | 19 |
| emit_member_ptr_at | `projects/ritz/ritz1/src/emitter_expr.ritz:475` | 8 | 417 |
| collect_from_stmt | `projects/ritz/ritz1/src/monomorph.ritz:1160` | 8 | 105 |
| resolve_expr_struct_name | `projects/ritz/ritz1/src/emitter_core.ritz:3742` | 8 | 78 |
| enum_variant_index | `projects/ritz/ritz1/src/ast_helpers.ritz:6924` | 8 | 23 |
| get_expr_type | `projects/ritz/ritz1/src/emitter_core.ritz:5861` | 7 | 190 |
| emit_match_arm_body | `projects/ritz/ritz1/src/emitter_match.ritz:684` | 7 | 178 |
| specialize_fn_one_param | `projects/ritz/ritz1/src/monomorph.ritz:2674` | 7 | 73 |
| resolve_scrutinee_enum | `projects/ritz/ritz1/src/emitter_match.ritz:1170` | 7 | 61 |
| call_callee_def | `projects/ritz/ritz1/src/emitter_core.ritz:3937` | 7 | 53 |
| asm_scan_line | `projects/ritz/ritz1/src/ast_helpers.ritz:4682` | 7 | 51 |
| track_method_init_local | `projects/ritz/ritz1/src/monomorph.ritz:609` | 7 | 37 |
| struct_deps_satisfied | `projects/ritz/ritz1/src/emitter.ritz:1981` | 7 | 20 |
| emit_stmt_inner | `projects/ritz/ritz1/src/emitter_stmt.ritz:5720` | 6 | 786 |
| emit_expr_index | `projects/ritz/ritz1/src/emitter_expr_access.ritz:778` | 6 | 705 |
| emit_assign | `projects/ritz/ritz1/src/emitter_stmt.ritz:2540` | 6 | 524 |
| emit_for_iterable | `projects/ritz/ritz1/src/emitter_stmt.ritz:3993` | 6 | 352 |
| emit_impl_method | `projects/ritz/ritz1/src/emitter.ritz:1125` | 6 | 297 |
| emit_fn | `projects/ritz/ritz1/src/emitter.ritz:748` | 6 | 291 |
| emit_expr_ident | `projects/ritz/ritz1/src/emitter_expr_access.ritz:59` | 6 | 256 |
| emit_ufcs_call | `projects/ritz/ritz1/src/emitter_expr_call.ritz:775` | 6 | 220 |
| tuple_subst | `projects/ritz/ritz1/src/monomorph.ritz:2551` | 6 | 105 |
| own_loop_exit | `projects/ritz/ritz1/src/ownership.ritz:1225` | 6 | 101 |
| clone_params_with_suffix | `projects/ritz/ritz1/src/monomorph.ritz:2890` | 6 | 94 |

## Distribution

- functions > 100 SLOC: 56 (2.2%); > 300 SLOC: 15 (0.6%)
- CC > 20: 148 (5.9%); CC > 50: 33 (1.3%)
- nesting depth >= 6: 50 (2.0%)

## Files by size

| file | lines | SLOC | fns | dup-window lines |
|---|---|---|---|---|
| `projects/ritz/ritz1/src/parser_gen.ritz` | 10070 | 8137 | 127 | 3210 |
| `projects/ritz/ritz1/src/emitter_expr_call.ritz` | 7228 | 5555 | 192 | 1260 |
| `projects/ritz/ritz1/src/ast_helpers.ritz` | 7495 | 5400 | 404 | 1080 |
| `projects/ritz/ritz1/src/emitter_stmt.ritz` | 6814 | 5007 | 136 | 978 |
| `projects/ritz/ritz1/src/emitter_core.ritz` | 6251 | 4127 | 287 | 342 |
| `projects/ritz/ritz1/src/monomorph.ritz` | 4333 | 3105 | 154 | 78 |
| `projects/ritz/ritz1/src/ownership.ritz` | 3817 | 3024 | 195 | 228 |
| `projects/ritz/ritz1/src/emitter.ritz` | 3718 | 2645 | 87 | 420 |
| `projects/ritz/ritz1/src/emitter_expr.ritz` | 2897 | 2184 | 57 | 396 |
| `projects/ritz/ritz1/src/ref_check.ritz` | 2379 | 1884 | 136 | 0 |
| `projects/ritz/ritz1/src/emitter_match.ritz` | 2514 | 1847 | 86 | 318 |
| `projects/ritz/ritz1/src/emitter_expr_arith.ritz` | 2277 | 1756 | 41 | 264 |
| `projects/ritz/ritz1/src/emitter_expr_access.ritz` | 1956 | 1550 | 30 | 678 |
| `projects/ritz/ritz1/src/emitter_print.ritz` | 1193 | 992 | 39 | 222 |
| `projects/ritz/ritz1/src/generic_infer.ritz` | 1147 | 960 | 46 | 66 |
| `projects/ritz/ritz1/src/main.ritz` | 1379 | 892 | 40 | 30 |
| `projects/ritz/ritz1/src/deref_field.ritz` | 924 | 745 | 52 | 12 |
| `projects/ritz/ritz1/src/fn_cache.ritz` | 1074 | 717 | 38 | 12 |
| `projects/ritz/ritz1/src/lexer_nfa.ritz` | 1009 | 642 | 25 | 84 |
| `projects/ritz/ritz1/src/bool_check.ritz` | 691 | 581 | 44 | 12 |
| `projects/ritz/ritz1/src/ast.ritz` | 926 | 485 | 3 | 12 |
| `projects/ritz/ritz1/src/index_through.ritz` | 640 | 462 | 37 | 0 |
| `projects/ritz/ritz1/src/narrowing.ritz` | 585 | 444 | 27 | 0 |
| `projects/ritz/ritz1/src/emitter_asm.ritz` | 529 | 433 | 19 | 6 |
| `projects/ritz/ritz1/src/let_check.ritz` | 525 | 391 | 25 | 18 |
| `projects/ritz/ritz1/src/literal_slot.ritz` | 431 | 348 | 30 | 6 |
| `projects/ritz/ritz1/src/binder_check.ritz` | 371 | 277 | 23 | 36 |
| `projects/ritz/ritz1/src/nfa.ritz` | 408 | 262 | 23 | 12 |
| `projects/ritz/ritz1/src/call_check.ritz` | 355 | 248 | 15 | 0 |
| `projects/ritz/ritz1/src/struct_index.ritz` | 256 | 188 | 19 | 12 |

## String / C-idiom smell counts per file

| file | ptr_len_param_pair | fixed_u8_buffer | strlen_call | memcpy_call | memcmp_or_streq_call | manual_byte_copy | manual_byte_compare | char_code_compare | cstr_literal | malloc_cast | malloc_magic_size | i32_as_bool | total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `projects/ritz/ritz1/src/emitter_expr_call.ritz` | 57 | 1 | 0 | 2 | 87 | 19 | 1 | 0 | 1149 | 0 | 0 | 163 | 1479 |
| `projects/ritz/ritz1/src/emitter_stmt.ritz` | 27 | 0 | 0 | 0 | 17 | 0 | 1 | 0 | 800 | 0 | 0 | 107 | 952 |
| `projects/ritz/ritz1/src/emitter_core.ritz` | 100 | 1 | 0 | 1 | 125 | 0 | 0 | 0 | 419 | 2 | 1 | 83 | 732 |
| `projects/ritz/ritz1/src/emitter.ritz` | 23 | 0 | 0 | 7 | 35 | 0 | 0 | 0 | 586 | 0 | 0 | 47 | 698 |
| `projects/ritz/ritz1/src/ast_helpers.ritz` | 134 | 1 | 0 | 3 | 18 | 1 | 0 | 0 | 255 | 1 | 1 | 113 | 527 |
| `projects/ritz/ritz1/src/emitter_expr_access.ritz` | 11 | 0 | 3 | 0 | 4 | 0 | 0 | 0 | 484 | 0 | 0 | 22 | 524 |
| `projects/ritz/ritz1/src/emitter_expr.ritz` | 11 | 0 | 2 | 2 | 4 | 0 | 0 | 0 | 457 | 0 | 2 | 36 | 514 |
| `projects/ritz/ritz1/src/emitter_expr_arith.ritz` | 3 | 0 | 11 | 0 | 11 | 0 | 0 | 0 | 413 | 0 | 0 | 46 | 484 |
| `projects/ritz/ritz1/src/emitter_print.ritz` | 7 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 365 | 0 | 0 | 27 | 401 |
| `projects/ritz/ritz1/src/ownership.ritz` | 27 | 0 | 0 | 3 | 8 | 6 | 0 | 0 | 238 | 0 | 0 | 105 | 387 |
| `projects/ritz/ritz1/src/emitter_match.ritz` | 29 | 0 | 0 | 3 | 16 | 0 | 0 | 0 | 243 | 2 | 0 | 77 | 370 |
| `projects/ritz/ritz1/src/monomorph.ritz` | 88 | 0 | 0 | 13 | 57 | 0 | 0 | 0 | 68 | 21 | 0 | 108 | 355 |
| `projects/ritz/ritz1/src/ref_check.ritz` | 13 | 0 | 0 | 0 | 22 | 0 | 1 | 0 | 47 | 0 | 0 | 37 | 120 |
| `projects/ritz/ritz1/src/emitter_asm.ritz` | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 83 | 0 | 0 | 14 | 100 |
| `projects/ritz/ritz1/src/generic_infer.ritz` | 12 | 0 | 0 | 11 | 13 | 0 | 0 | 0 | 25 | 0 | 0 | 30 | 91 |
| `projects/ritz/ritz1/src/deref_field.ritz` | 9 | 1 | 1 | 5 | 10 | 0 | 0 | 0 | 37 | 0 | 0 | 27 | 90 |
| `projects/ritz/ritz1/src/bool_check.ritz` | 8 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 54 | 0 | 0 | 9 | 80 |
| `projects/ritz/ritz1/src/fn_cache.ritz` | 10 | 4 | 5 | 9 | 2 | 0 | 0 | 0 | 28 | 1 | 1 | 11 | 71 |
| `projects/ritz/ritz1/src/binder_check.ritz` | 13 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 17 | 0 | 0 | 14 | 51 |
| `projects/ritz/ritz1/src/call_check.ritz` | 6 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 29 | 0 | 0 | 10 | 50 |
| `projects/ritz/ritz1/src/struct_index.ritz` | 7 | 0 | 1 | 2 | 3 | 0 | 0 | 0 | 24 | 0 | 0 | 12 | 49 |
| `projects/ritz/ritz1/src/let_check.ritz` | 6 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 32 | 0 | 0 | 8 | 48 |
| `projects/ritz/ritz1/src/index_through.ritz` | 6 | 0 | 3 | 0 | 2 | 0 | 0 | 0 | 18 | 0 | 0 | 8 | 37 |
| `projects/ritz/ritz1/src/main.ritz` | 5 | 3 | 0 | 3 | 5 | 0 | 0 | 0 | 15 | 0 | 0 | 6 | 37 |
| `projects/ritz/ritz1/src/literal_slot.ritz` | 4 | 1 | 0 | 0 | 4 | 0 | 0 | 0 | 15 | 0 | 0 | 5 | 29 |
| `projects/ritz/ritz1/src/narrowing.ritz` | 3 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 19 | 0 | 0 | 4 | 28 |
| `projects/ritz/ritz1/src/lexer_nfa.ritz` | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 12 | 24 |
| `projects/ritz/ritz1/src/enum_as_int.ritz` | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 2 | 17 |
| `projects/ritz/ritz1/src/ll_copy_scan.ritz` | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 0 | 17 |
| `projects/ritz/ritz1/src/ast.ritz` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 15 | 16 |
| **total** | 640 | 14 | 26 | 64 | 470 | 35 | 3 | 0 | 5979 | 27 | 5 | 1185 | 8448 |

## Duplicated 6-line windows (top 30 clusters by occurrences)

- **43×** `emit_str(s, c"; Inline syscall implementations (weak_odr — linker merges duplica` — `projects/ritz/ritz1/src/emitter.ritz:1610`, `projects/ritz/ritz1/src/emitter.ritz:1616`, `projects/ritz/ritz1/src/emitter.ritz:1622`, `projects/ritz/ritz1/src/emitter.ritz:1629`, `projects/ritz/ritz1/src/emitter.ritz:1635`, `projects/ritz/ritz1/src/emitter.ritz:1641`, `projects/ritz/ritz1/src/emitter.ritz:1647`, `projects/ritz/ritz1/src/emitter.ritz:1653` (+35 more)
- **17×** `let trunc: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter.ritz:1046`, `projects/ritz/ritz1/src/emitter.ritz:1397`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2618`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2632`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2644`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2965`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2978`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2991` (+9 more)
- **17×** `emit_str(s, c"  ")` — `projects/ritz/ritz1/src/emitter.ritz:1047`, `projects/ritz/ritz1/src/emitter.ritz:1398`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2619`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2633`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2645`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2966`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2979`, `projects/ritz/ritz1/src/emitter_stmt.ritz:2992` (+9 more)
- **15×** `eprints_cstr(c"error: ")` — `projects/ritz/ritz1/src/emitter_core.ritz:3615`, `projects/ritz/ritz1/src/emitter_core.ritz:3668`, `projects/ritz/ritz1/src/emitter_core.ritz:3706`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1710`, `projects/ritz/ritz1/src/emitter_expr_arith.ritz:1538`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:505`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1896`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4163` (+7 more)
- **13×** `eprints_cstr(c"error: ")` — `projects/ritz/ritz1/src/ast_helpers.ritz:471`, `projects/ritz/ritz1/src/ast_helpers.ritz:490`, `projects/ritz/ritz1/src/ast_helpers.ritz:576`, `projects/ritz/ritz1/src/ast_helpers.ritz:1019`, `projects/ritz/ritz1/src/ast_helpers.ritz:1181`, `projects/ritz/ritz1/src/ast_helpers.ritz:1227`, `projects/ritz/ritz1/src/ast_helpers.ritz:1346`, `projects/ritz/ritz1/src/ast_helpers.ritz:1765` (+5 more)
- **13×** `else` — `projects/ritz/ritz1/src/ast_helpers.ritz:474`, `projects/ritz/ritz1/src/ast_helpers.ritz:493`, `projects/ritz/ritz1/src/ast_helpers.ritz:579`, `projects/ritz/ritz1/src/ast_helpers.ritz:1022`, `projects/ritz/ritz1/src/ast_helpers.ritz:1349`, `projects/ritz/ritz1/src/ast_helpers.ritz:2817`, `projects/ritz/ritz1/src/ast_helpers.ritz:2849`, `projects/ritz/ritz1/src/ast_helpers.ritz:2938` (+5 more)
- **13×** `let ext: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:1341`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1349`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1357`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1365`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1373`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1381`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1879`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1887` (+5 more)
- **13×** `emit_str(s, c"  ")` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:1342`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1350`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1358`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1366`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1374`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1382`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1880`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1888` (+5 more)
- **12×** `eprints_cstr(c"<input>")` — `projects/ritz/ritz1/src/ast_helpers.ritz:475`, `projects/ritz/ritz1/src/ast_helpers.ritz:494`, `projects/ritz/ritz1/src/ast_helpers.ritz:580`, `projects/ritz/ritz1/src/ast_helpers.ritz:1023`, `projects/ritz/ritz1/src/ast_helpers.ritz:1350`, `projects/ritz/ritz1/src/ast_helpers.ritz:2818`, `projects/ritz/ritz1/src/ast_helpers.ritz:2939`, `projects/ritz/ritz1/src/ast_helpers.ritz:4494` (+4 more)
- **12×** `let file: *u8 = emitter_source_file()` — `projects/ritz/ritz1/src/emitter_core.ritz:3616`, `projects/ritz/ritz1/src/emitter_core.ritz:3669`, `projects/ritz/ritz1/src/emitter_core.ritz:3707`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1711`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1815`, `projects/ritz/ritz1/src/emitter_expr_arith.ritz:1539`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4164`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5851` (+4 more)
- **11×** `g_attr_errors = g_attr_errors + 1` — `projects/ritz/ritz1/src/ast_helpers.ritz:470`, `projects/ritz/ritz1/src/ast_helpers.ritz:489`, `projects/ritz/ritz1/src/ast_helpers.ritz:575`, `projects/ritz/ritz1/src/ast_helpers.ritz:1018`, `projects/ritz/ritz1/src/ast_helpers.ritz:1180`, `projects/ritz/ritz1/src/ast_helpers.ritz:1226`, `projects/ritz/ritz1/src/ast_helpers.ritz:1764`, `projects/ritz/ritz1/src/ast_helpers.ritz:2813` (+3 more)
- **11×** `if g_parse_file != null` — `projects/ritz/ritz1/src/ast_helpers.ritz:472`, `projects/ritz/ritz1/src/ast_helpers.ritz:491`, `projects/ritz/ritz1/src/ast_helpers.ritz:577`, `projects/ritz/ritz1/src/ast_helpers.ritz:1020`, `projects/ritz/ritz1/src/ast_helpers.ritz:1228`, `projects/ritz/ritz1/src/ast_helpers.ritz:1347`, `projects/ritz/ritz1/src/ast_helpers.ritz:2815`, `projects/ritz/ritz1/src/ast_helpers.ritz:2847` (+3 more)
- **11×** `emit_str(s, c"\n")` — `projects/ritz/ritz1/src/emitter_core.ritz:3614`, `projects/ritz/ritz1/src/emitter_core.ritz:3667`, `projects/ritz/ritz1/src/emitter_core.ritz:3705`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1709`, `projects/ritz/ritz1/src/emitter_expr_arith.ritz:1537`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:504`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4162`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5849` (+3 more)
- **11×** `emit_ir_error(s, c"simd_load(u) requires a pointer argument")` — `projects/ritz/ritz1/src/emitter_expr_call.ritz:3138`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:3183`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:3230`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:3261`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:3310`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:3362`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:3417`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:3490` (+3 more)
- **10×** `eprints_cstr(g_parse_file)` — `projects/ritz/ritz1/src/ast_helpers.ritz:473`, `projects/ritz/ritz1/src/ast_helpers.ritz:492`, `projects/ritz/ritz1/src/ast_helpers.ritz:578`, `projects/ritz/ritz1/src/ast_helpers.ritz:1021`, `projects/ritz/ritz1/src/ast_helpers.ritz:1348`, `projects/ritz/ritz1/src/ast_helpers.ritz:2816`, `projects/ritz/ritz1/src/ast_helpers.ritz:2848`, `projects/ritz/ritz1/src/ast_helpers.ritz:2937` (+2 more)
- **10×** `p.error = 1` — `projects/ritz/ritz1/src/parser_gen.ritz:7122`, `projects/ritz/ritz1/src/parser_gen.ritz:7208`, `projects/ritz/ritz1/src/parser_gen.ritz:7294`, `projects/ritz/ritz1/src/parser_gen.ritz:7351`, `projects/ritz/ritz1/src/parser_gen.ritz:7408`, `projects/ritz/ritz1/src/parser_gen.ritz:7464`, `projects/ritz/ritz1/src/parser_gen.ritz:7637`, `projects/ritz/ritz1/src/parser_gen.ritz:7723` (+2 more)
- **9×** `let field_ptr: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr.ritz:89`, `projects/ritz/ritz1/src/emitter_expr.ritz:105`, `projects/ritz/ritz1/src/emitter_expr.ritz:498`, `projects/ritz/ritz1/src/emitter_expr.ritz:2536`, `projects/ritz/ritz1/src/emitter_expr.ritz:2592`, `projects/ritz/ritz1/src/emitter_expr_arith.ritz:1931`, `projects/ritz/ritz1/src/emitter_expr_arith.ritz:1946`, `projects/ritz/ritz1/src/emitter_stmt.ritz:6298` (+1 more)
- **8×** `let binary: *Expr = parser_alloc(p, sizeof(Expr)) as *Expr` — `projects/ritz/ritz1/src/ast_helpers.ritz:5065`, `projects/ritz/ritz1/src/ast_helpers.ritz:5105`, `projects/ritz/ritz1/src/ast_helpers.ritz:5128`, `projects/ritz/ritz1/src/ast_helpers.ritz:5161`, `projects/ritz/ritz1/src/ast_helpers.ritz:5203`, `projects/ritz/ritz1/src/ast_helpers.ritz:5236`, `projects/ritz/ritz1/src/ast_helpers.ritz:5278`, `projects/ritz/ritz1/src/ast_helpers.ritz:5293`
- **8×** `p.pos = start_pos` — `projects/ritz/ritz1/src/parser_gen.ritz:163`, `projects/ritz/ritz1/src/parser_gen.ritz:459`, `projects/ritz/ritz1/src/parser_gen.ritz:589`, `projects/ritz/ritz1/src/parser_gen.ritz:698`, `projects/ritz/ritz1/src/parser_gen.ritz:1743`, `projects/ritz/ritz1/src/parser_gen.ritz:2014`, `projects/ritz/ritz1/src/parser_gen.ritz:4036`, `projects/ritz/ritz1/src/parser_gen.ritz:4202`
- **8×** `p.pos = start_pos` — `projects/ritz/ritz1/src/parser_gen.ritz:188`, `projects/ritz/ritz1/src/parser_gen.ritz:488`, `projects/ritz/ritz1/src/parser_gen.ritz:722`, `projects/ritz/ritz1/src/parser_gen.ritz:2047`, `projects/ritz/ritz1/src/parser_gen.ritz:2312`, `projects/ritz/ritz1/src/parser_gen.ritz:4074`, `projects/ritz/ritz1/src/parser_gen.ritz:4716`, `projects/ritz/ritz1/src/parser_gen.ritz:8393`
- **8×** `p.pos = start_pos` — `projects/ritz/ritz1/src/parser_gen.ritz:1443`, `projects/ritz/ritz1/src/parser_gen.ritz:2197`, `projects/ritz/ritz1/src/parser_gen.ritz:3571`, `projects/ritz/ritz1/src/parser_gen.ritz:4160`, `projects/ritz/ritz1/src/parser_gen.ritz:8707`, `projects/ritz/ritz1/src/parser_gen.ritz:8746`, `projects/ritz/ritz1/src/parser_gen.ritz:9493`, `projects/ritz/ritz1/src/parser_gen.ritz:9617`
- **8×** `let start_pos: i32 = p.pos` — `projects/ritz/ritz1/src/parser_gen.ritz:7112`, `projects/ritz/ritz1/src/parser_gen.ritz:7198`, `projects/ritz/ritz1/src/parser_gen.ritz:7284`, `projects/ritz/ritz1/src/parser_gen.ritz:7341`, `projects/ritz/ritz1/src/parser_gen.ritz:7398`, `projects/ritz/ritz1/src/parser_gen.ritz:7627`, `projects/ritz/ritz1/src/parser_gen.ritz:7713`, `projects/ritz/ritz1/src/parser_gen.ritz:7799`
- **7×** `let file: *u8 = emitter_source_file()` — `projects/ritz/ritz1/src/emitter_asm.ritz:180`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:506`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:1897`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5880`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5934`, `projects/ritz/ritz1/src/emitter_match.ritz:568`, `projects/ritz/ritz1/src/let_check.ritz:145`
- **7×** `let trunc: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_call.ritz:827`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:835`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:843`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4599`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4607`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4615`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4793`
- **7×** `emit_str(s, c"  ")` — `projects/ritz/ritz1/src/emitter_expr_call.ritz:828`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:836`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:844`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4600`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4608`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4616`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4794`
- **7×** `let ext: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_call.ritz:5042`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5050`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5058`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5066`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5074`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5082`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5090`
- **7×** `if p.error == 0` — `projects/ritz/ritz1/src/parser_gen.ritz:164`, `projects/ritz/ritz1/src/parser_gen.ritz:460`, `projects/ritz/ritz1/src/parser_gen.ritz:590`, `projects/ritz/ritz1/src/parser_gen.ritz:699`, `projects/ritz/ritz1/src/parser_gen.ritz:2015`, `projects/ritz/ritz1/src/parser_gen.ritz:4037`, `projects/ritz/ritz1/src/parser_gen.ritz:4203`
- **7×** `if p.error != 0` — `projects/ritz/ritz1/src/parser_gen.ritz:3592`, `projects/ritz/ritz1/src/parser_gen.ritz:3823`, `projects/ritz/ritz1/src/parser_gen.ritz:4181`, `projects/ritz/ritz1/src/parser_gen.ritz:4322`, `projects/ritz/ritz1/src/parser_gen.ritz:5793`, `projects/ritz/ritz1/src/parser_gen.ritz:8728`, `projects/ritz/ritz1/src/parser_gen.ritz:8763`
- **6×** `else` — `projects/ritz/ritz1/src/emitter_core.ritz:3619`, `projects/ritz/ritz1/src/emitter_core.ritz:5827`, `projects/ritz/ritz1/src/emitter_expr_arith.ritz:1542`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:4167`, `projects/ritz/ritz1/src/emitter_expr_call.ritz:5854`, `projects/ritz/ritz1/src/must_use.ritz:44`
- **6×** `let ext: i32 = next_reg(s)` — `projects/ritz/ritz1/src/emitter_expr_access.ritz:201`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:209`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:282`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:290`, `projects/ritz/ritz1/src/emitter_expr_access.ritz:1655`, `projects/ritz/ritz1/src/emitter_expr_arith.ritz:2066`

Total duplicate clusters: 562
