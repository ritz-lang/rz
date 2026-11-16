# ritz-metrics: 39 files, 29494 SLOC, 1340 functions

## Longest functions (top 25)

| fn | where | SLOC | CC | depth |
|---|---|---|---|---|
| _try_emit_simd_builtin | `projects/ritz/ritz0/emitter_llvmlite.py:12463` | 477 | 145 | 5 |
| _emit_stmt_inner | `projects/ritz/ritz0/emitter_llvmlite.py:6274` | 425 | 151 | 11 |
| _dispatch_method_call | `projects/ritz/ritz0/emitter_llvmlite.py:13741` | 269 | 127 | 13 |
| _emit_expr_core | `projects/ritz/ritz0/emitter_llvmlite.py:8393` | 264 | 132 | 6 |
| _emit_call_inner | `projects/ritz/ritz0/emitter_llvmlite.py:12098` | 224 | 88 | 10 |
| _check_expr | `projects/ritz/ritz0/move_checker.py:1267` | 220 | 106 | 11 |
| compile_file | `projects/ritz/ritz0/ritz0.py:117` | 194 | 55 | 9 |
| _emit_index_core | `projects/ritz/ritz0/emitter_llvmlite.py:9283` | 193 | 78 | 7 |
| _infer_ritz_type | `projects/ritz/ritz0/emitter_llvmlite.py:1616` | 182 | 111 | 8 |
| _emit_closure | `projects/ritz/ritz0/emitter_llvmlite.py:10931` | 168 | 33 | 5 |
| _emit_lvalue_addr | `projects/ritz/ritz0/emitter_llvmlite.py:10240` | 153 | 65 | 9 |
| _register_items_from_metadata | `projects/ritz/ritz0/import_resolver.py:1064` | 153 | 33 | 10 |
| _emit_for_iterable | `projects/ritz/ritz0/emitter_llvmlite.py:7800` | 151 | 43 | 7 |
| _infer_type | `projects/ritz/ritz0/type_checker.py:438` | 149 | 65 | 8 |
| _emit_function_body_inner | `projects/ritz/ritz0/emitter_llvmlite.py:5316` | 148 | 40 | 6 |
| _lex_string | `projects/ritz/ritz0/lexer.py:190` | 140 | 44 | 8 |
| _emit_enum_match | `projects/ritz/ritz0/emitter_llvmlite.py:15812` | 134 | 47 | 12 |
| extract_metadata | `projects/ritz/ritz0/metadata.py:190` | 126 | 29 | 5 |
| parse_primary | `projects/ritz/ritz0/parser.py:1215` | 126 | 43 | 6 |
| _parse_type_primary | `projects/ritz/ritz0/parser.py:678` | 120 | 28 | 6 |
| _emit_integer_match | `projects/ritz/ritz0/emitter_llvmlite.py:16233` | 113 | 51 | 7 |
| _check_expr | `projects/ritz/ritz0/name_resolver.py:330` | 112 | 63 | 5 |
| _check_one_stmt | `projects/ritz/ritz0/move_checker.py:1022` | 108 | 39 | 11 |
| parse_postfix | `projects/ritz/ritz0/parser.py:1062` | 108 | 38 | 10 |
| _generate_state_handler | `projects/ritz/ritz0/async_transform_v2.py:427` | 107 | 4 | 5 |

## Highest cyclomatic complexity (top 25)

| fn | where | CC | SLOC | depth |
|---|---|---|---|---|
| _emit_stmt_inner | `projects/ritz/ritz0/emitter_llvmlite.py:6274` | 151 | 425 | 11 |
| _try_emit_simd_builtin | `projects/ritz/ritz0/emitter_llvmlite.py:12463` | 145 | 477 | 5 |
| _emit_expr_core | `projects/ritz/ritz0/emitter_llvmlite.py:8393` | 132 | 264 | 6 |
| _dispatch_method_call | `projects/ritz/ritz0/emitter_llvmlite.py:13741` | 127 | 269 | 13 |
| _infer_ritz_type | `projects/ritz/ritz0/emitter_llvmlite.py:1616` | 111 | 182 | 8 |
| _check_expr | `projects/ritz/ritz0/move_checker.py:1267` | 106 | 220 | 11 |
| _emit_call_inner | `projects/ritz/ritz0/emitter_llvmlite.py:12098` | 88 | 224 | 10 |
| _emit_index_core | `projects/ritz/ritz0/emitter_llvmlite.py:9283` | 78 | 193 | 7 |
| _emit_lvalue_addr | `projects/ritz/ritz0/emitter_llvmlite.py:10240` | 65 | 153 | 9 |
| _infer_type | `projects/ritz/ritz0/type_checker.py:438` | 65 | 149 | 8 |
| _check_expr | `projects/ritz/ritz0/name_resolver.py:330` | 63 | 112 | 5 |
| merge | `projects/ritz/ritz0/batching.py:167` | 60 | 81 | 9 |
| _convert_type | `projects/ritz/ritz0/emitter_llvmlite.py:14592` | 57 | 93 | 6 |
| compile_file | `projects/ritz/ritz0/ritz0.py:117` | 55 | 194 | 9 |
| _types_compatible | `projects/ritz/ritz0/type_checker.py:2079` | 54 | 56 | 4 |
| evaluate | `projects/ritz/ritz0/const_eval.py:69` | 52 | 100 | 4 |
| _emit_integer_match | `projects/ritz/ritz0/emitter_llvmlite.py:16233` | 51 | 113 | 7 |
| _index_through | `projects/ritz/ritz0/emitter_llvmlite.py:9112` | 49 | 73 | 8 |
| _check_call | `projects/ritz/ritz0/type_checker.py:753` | 49 | 87 | 9 |
| _emit_enum_match | `projects/ritz/ritz0/emitter_llvmlite.py:15812` | 47 | 134 | 12 |
| _infer_value_type | `projects/ritz/ritz0/monomorph.py:1244` | 46 | 80 | 8 |
| _check_method_call | `projects/ritz/ritz0/type_checker.py:902` | 46 | 90 | 8 |
| emit_module | `projects/ritz/ritz0/emitter_llvmlite.py:2611` | 45 | 107 | 9 |
| _lex_operator | `projects/ritz/ritz0/lexer.py:540` | 45 | 103 | 3 |
| _lex_string | `projects/ritz/ritz0/lexer.py:190` | 44 | 140 | 8 |

## Deepest nesting (top 25)

| fn | where | depth | SLOC |
|---|---|---|---|
| _dispatch_method_call | `projects/ritz/ritz0/emitter_llvmlite.py:13741` | 13 | 269 |
| _emit_enum_match | `projects/ritz/ritz0/emitter_llvmlite.py:15812` | 12 | 134 |
| _emit_drop_glue | `projects/ritz/ritz0/emitter_llvmlite.py:4911` | 12 | 54 |
| _emit_stmt_inner | `projects/ritz/ritz0/emitter_llvmlite.py:6274` | 11 | 425 |
| _check_expr | `projects/ritz/ritz0/move_checker.py:1267` | 11 | 220 |
| _check_one_stmt | `projects/ritz/ritz0/move_checker.py:1022` | 11 | 108 |
| _emit_enum_variant_constructor | `projects/ritz/ritz0/emitter_llvmlite.py:3353` | 11 | 52 |
| _emit_enum_variant_constructor_for_type | `projects/ritz/ritz0/emitter_llvmlite.py:3585` | 11 | 44 |
| _emit_enum_drop_glue | `projects/ritz/ritz0/emitter_llvmlite.py:5008` | 11 | 39 |
| _register_method_instantiation | `projects/ritz/ritz0/monomorph.py:1442` | 11 | 32 |
| _generic_static_instance | `projects/ritz/ritz0/emitter_llvmlite.py:13470` | 11 | 21 |
| _assign_tuple_element | `projects/ritz/ritz0/emitter_llvmlite.py:4439` | 11 | 19 |
| _deref_member_target | `projects/ritz/ritz0/emitter_llvmlite.py:9003` | 11 | 16 |
| _deref_field | `projects/ritz/ritz0/emitter_llvmlite.py:9020` | 11 | 14 |
| _emit_call_inner | `projects/ritz/ritz0/emitter_llvmlite.py:12098` | 10 | 224 |
| _register_items_from_metadata | `projects/ritz/ritz0/import_resolver.py:1064` | 10 | 153 |
| parse_postfix | `projects/ritz/ritz0/parser.py:1062` | 10 | 108 |
| _emit_array_fill_to_alloca | `projects/ritz/ritz0/emitter_llvmlite.py:10041` | 10 | 44 |
| _check_implicit_narrowing | `projects/ritz/ritz0/emitter_llvmlite.py:14888` | 10 | 29 |
| _specialize_enum | `projects/ritz/ritz0/monomorph.py:1850` | 10 | 19 |
| _rewrite_enum | `projects/ritz/ritz0/monomorph.py:2207` | 10 | 17 |
| compile_file | `projects/ritz/ritz0/ritz0.py:117` | 9 | 194 |
| _emit_lvalue_addr | `projects/ritz/ritz0/emitter_llvmlite.py:10240` | 9 | 153 |
| emit_module | `projects/ritz/ritz0/emitter_llvmlite.py:2611` | 9 | 107 |
| _register_item | `projects/ritz/ritz0/import_resolver.py:1245` | 9 | 103 |

## Distribution

- functions > 100 SLOC: 29 (2.2%); > 300 SLOC: 2 (0.1%)
- CC > 20: 88 (6.6%); CC > 50: 17 (1.3%)
- nesting depth >= 6: 185 (13.8%)

## Files by size

| file | lines | SLOC | fns | dup-window lines |
|---|---|---|---|---|
| `projects/ritz/ritz0/emitter_llvmlite.py` | 17385 | 13038 | 518 | 1224 |
| `projects/ritz/ritz0/parser.py` | 3058 | 2286 | 94 | 138 |
| `projects/ritz/ritz0/monomorph.py` | 2554 | 1990 | 81 | 48 |
| `projects/ritz/ritz0/move_checker.py` | 2264 | 1802 | 111 | 42 |
| `projects/ritz/ritz0/type_checker.py` | 2232 | 1767 | 105 | 24 |
| `projects/ritz/ritz0/import_resolver.py` | 1605 | 1198 | 41 | 48 |
| `projects/ritz/ritz0/ritz_ast.py` | 1193 | 842 | 29 | 24 |
| `projects/ritz/ritz0/lexer.py` | 900 | 716 | 22 | 84 |
| `projects/ritz/ritz0/batching.py` | 808 | 648 | 40 | 0 |
| `projects/ritz/ritz0/emitter/fn_cache.py` | 846 | 594 | 30 | 12 |
| `projects/ritz/ritz0/async_transform_v2.py` | 778 | 579 | 29 | 0 |
| `projects/ritz/ritz0/symbol_table.py` | 539 | 430 | 29 | 0 |
| `projects/ritz/ritz0/ritz0.py` | 583 | 404 | 6 | 12 |
| `projects/ritz/ritz0/name_resolver.py` | 532 | 401 | 20 | 0 |
| `projects/ritz/ritz0/metadata.py` | 508 | 384 | 16 | 24 |
| `projects/ritz/ritz0/module_interface.py` | 495 | 361 | 27 | 0 |
| `projects/ritz/ritz0/const_eval.py` | 329 | 267 | 14 | 0 |
| `projects/ritz/ritz0/ritz0_inproc.py` | 314 | 264 | 11 | 0 |
| `projects/ritz/ritz0/fast_link.py` | 262 | 227 | 10 | 0 |
| `projects/ritz/ritz0/binder_names.py` | 215 | 179 | 17 | 0 |
| `projects/ritz/ritz0/tokens.py` | 221 | 175 | 2 | 0 |
| `projects/ritz/ritz0/tail_value.py` | 167 | 141 | 8 | 18 |
| `projects/ritz/ritz0/match_coverage.py` | 143 | 102 | 11 | 0 |
| `projects/ritz/ritz0/deref_rules.py` | 123 | 95 | 11 | 0 |
| `projects/ritz/ritz0/reachability.py` | 110 | 87 | 7 | 18 |

## String / C-idiom smell counts per file

| file | bare_except | subprocess_shell_true | global_stmt | total |
|---|---|---|---|---|
| `projects/ritz/ritz0/fast_link.py` | 0 | 0 | 3 | 3 |
| `projects/ritz/ritz0/emitter_llvmlite.py` | 0 | 0 | 2 | 2 |
| `projects/ritz/ritz0/monomorph.py` | 0 | 0 | 2 | 2 |
| `projects/ritz/ritz0/ritz0_inproc.py` | 0 | 0 | 2 | 2 |
| `projects/ritz/ritz0/batching.py` | 0 | 0 | 1 | 1 |
| `projects/ritz/ritz0/module_interface.py` | 0 | 0 | 1 | 1 |
| `projects/ritz/ritz0/move_checker.py` | 0 | 0 | 1 | 1 |
| `projects/ritz/ritz0/spawn_guard.py` | 0 | 0 | 1 | 1 |
| **total** | 0 | 0 | 13 | 13 |

## Duplicated 6-line windows (top 25 clusters by occurrences)

- **6×** `if input_type == v4i32:` — `projects/ritz/ritz0/emitter_llvmlite.py:12906`, `projects/ritz/ritz0/emitter_llvmlite.py:12935`, `projects/ritz/ritz0/emitter_llvmlite.py:12964`, `projects/ritz/ritz0/emitter_llvmlite.py:12993`, `projects/ritz/ritz0/emitter_llvmlite.py:13020`, `projects/ritz/ritz0/emitter_llvmlite.py:13074`
- **5×** `key_i64 = key` — `projects/ritz/ritz0/emitter_llvmlite.py:12894`, `projects/ritz/ritz0/emitter_llvmlite.py:12924`, `projects/ritz/ritz0/emitter_llvmlite.py:12953`, `projects/ritz/ritz0/emitter_llvmlite.py:12982`, `projects/ritz/ritz0/emitter_llvmlite.py:13009`
- **4×** `return self.builder.icmp_signed('!=', left, right)` — `projects/ritz/ritz0/emitter_llvmlite.py:8663`, `projects/ritz/ritz0/emitter_llvmlite.py:8670`, `projects/ritz/ritz0/emitter_llvmlite.py:8676`, `projects/ritz/ritz0/emitter_llvmlite.py:8682`
- **4×** `elif op == '<':` — `projects/ritz/ritz0/emitter_llvmlite.py:8664`, `projects/ritz/ritz0/emitter_llvmlite.py:8671`, `projects/ritz/ritz0/emitter_llvmlite.py:8677`, `projects/ritz/ritz0/emitter_llvmlite.py:8683`
- **4×** `elif fname == 'aesenc':` — `projects/ritz/ritz0/emitter_llvmlite.py:12878`, `projects/ritz/ritz0/emitter_llvmlite.py:12910`, `projects/ritz/ritz0/emitter_llvmlite.py:12939`, `projects/ritz/ritz0/emitter_llvmlite.py:12968`
- **4×** `if len(args) != 2:` — `projects/ritz/ritz0/emitter_llvmlite.py:12882`, `projects/ritz/ritz0/emitter_llvmlite.py:12913`, `projects/ritz/ritz0/emitter_llvmlite.py:12942`, `projects/ritz/ritz0/emitter_llvmlite.py:12971`
- **4×** `raise ValueError("aesenc() requires 2 arguments (state, key)")` — `projects/ritz/ritz0/emitter_llvmlite.py:12883`, `projects/ritz/ritz0/emitter_llvmlite.py:12914`, `projects/ritz/ritz0/emitter_llvmlite.py:12943`, `projects/ritz/ritz0/emitter_llvmlite.py:12972`
- **4×** `input_type = state.type` — `projects/ritz/ritz0/emitter_llvmlite.py:12888`, `projects/ritz/ritz0/emitter_llvmlite.py:12918`, `projects/ritz/ritz0/emitter_llvmlite.py:12947`, `projects/ritz/ritz0/emitter_llvmlite.py:12976`
- **4×** `if input_type == v4i32:` — `projects/ritz/ritz0/emitter_llvmlite.py:12889`, `projects/ritz/ritz0/emitter_llvmlite.py:12919`, `projects/ritz/ritz0/emitter_llvmlite.py:12948`, `projects/ritz/ritz0/emitter_llvmlite.py:12977`
- **4×** `raise ValueError("aesenc() requires v4i32 or v2i64 arguments")` — `projects/ritz/ritz0/emitter_llvmlite.py:12896`, `projects/ritz/ritz0/emitter_llvmlite.py:12926`, `projects/ritz/ritz0/emitter_llvmlite.py:12955`, `projects/ritz/ritz0/emitter_llvmlite.py:12984`
- **4×** `intrinsic = self.module.globals[intrinsic_name]` — `projects/ritz/ritz0/emitter_llvmlite.py:12900`, `projects/ritz/ritz0/emitter_llvmlite.py:12930`, `projects/ritz/ritz0/emitter_llvmlite.py:12959`, `projects/ritz/ritz0/emitter_llvmlite.py:12988`
- **4×** `else:` — `projects/ritz/ritz0/emitter_llvmlite.py:12901`, `projects/ritz/ritz0/emitter_llvmlite.py:12931`, `projects/ritz/ritz0/emitter_llvmlite.py:12960`, `projects/ritz/ritz0/emitter_llvmlite.py:12989`
- **4×** `chars.append('\n')` — `projects/ritz/ritz0/lexer.py:231`, `projects/ritz/ritz0/lexer.py:237`, `projects/ritz/ritz0/lexer.py:406`, `projects/ritz/ritz0/lexer.py:412`
- **3×** `self._push_drop_scope()` — `projects/ritz/ritz0/emitter_llvmlite.py:7602`, `projects/ritz/ritz0/emitter_llvmlite.py:7731`, `projects/ritz/ritz0/emitter_llvmlite.py:7944`
- **3×** `if not self.builder.block.is_terminated and stmt.body.expr:` — `projects/ritz/ritz0/emitter_llvmlite.py:7609`, `projects/ritz/ritz0/emitter_llvmlite.py:7738`, `projects/ritz/ritz0/emitter_llvmlite.py:7950`
- **3×** `return self.builder.fcmp_ordered('<', left, right)` — `projects/ritz/ritz0/emitter_llvmlite.py:8666`, `projects/ritz/ritz0/emitter_llvmlite.py:8673`, `projects/ritz/ritz0/emitter_llvmlite.py:8679`
- **3×** `return self.builder.bitcast(result, v4i32)` — `projects/ritz/ritz0/emitter_llvmlite.py:12907`, `projects/ritz/ritz0/emitter_llvmlite.py:12936`, `projects/ritz/ritz0/emitter_llvmlite.py:12965`
- **3×** `while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):` — `projects/ritz/ritz0/parser.py:1096`, `projects/ritz/ritz0/parser.py:1171`, `projects/ritz/ritz0/parser.py:1394`
- **2×** `if tok.type in _SKIP_TOKENS:` — `projects/ritz/ritz0/emitter/fn_cache.py:99`, `projects/ritz/ritz0/emitter/fn_cache.py:128`
- **2×** `if isinstance(expr, rast.IntLit):` — `projects/ritz/ritz0/emitter_llvmlite.py:1628`, `projects/ritz/ritz0/move_checker.py:521`
- **2×** `return rast.NamedType(expr.span, 'f64', [])` — `projects/ritz/ritz0/emitter_llvmlite.py:1632`, `projects/ritz/ritz0/move_checker.py:524`
- **2×** `return rast.NamedType(expr.span, 'StrView', [])` — `projects/ritz/ritz0/emitter_llvmlite.py:1641`, `projects/ritz/ritz0/type_checker.py:463`
- **2×** `span=dummy_span,` — `projects/ritz/ritz0/emitter_llvmlite.py:2980`, `projects/ritz/ritz0/emitter_llvmlite.py:2992`
- **2×** `enum_type, variants = self.enum_types[enum_name]` — `projects/ritz/ritz0/emitter_llvmlite.py:3370`, `projects/ritz/ritz0/emitter_llvmlite.py:3594`
- **2×** `variant = self._get_enum_variant(enum_name, variant_name)` — `projects/ritz/ritz0/emitter_llvmlite.py:3372`, `projects/ritz/ritz0/emitter_llvmlite.py:3596`

Total duplicate clusters: 126
