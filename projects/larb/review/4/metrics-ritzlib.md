# ritz-metrics: 81 files, 14089 SLOC, 1546 functions

## Longest functions (top 25)

| fn | where | SLOC | CC | depth |
|---|---|---|---|---|
| meta_free | `projects/ritz/ritzlib/meta.ritz:135` | 110 | 55 | 8 |
| args_parse | `projects/ritz/ritzlib/args.ritz:158` | 98 | 30 | 7 |
| jp_parse_object | `projects/ritz/ritzlib/json.ritz:381` | 71 | 13 | 4 |
| jp_parse_string | `projects/ritz/ritzlib/json.ritz:219` | 60 | 17 | 5 |
| spawn_full | `projects/ritz/ritzlib/process.ritz:117` | 59 | 8 | 3 |
| test_dir_next_entry_yields_typed_entries | `projects/ritz/ritzlib/tests/test_fs_dirent.ritz:44` | 50 | 15 | 4 |
| uring_init | `projects/ritz/ritzlib/uring.ritz:229` | 48 | 6 | 2 |
| jp_parse_array | `projects/ritz/ritzlib/json.ritz:323` | 43 | 10 | 4 |
| env_load | `projects/ritz/ritzlib/os/env.ritz:53` | 39 | 7 | 4 |
| socket_connect_timeout | `projects/ritz/ritzlib/net.ritz:408` | 38 | 10 | 2 |
| make_sandbox_path | `projects/ritz/ritzlib/testlib.ritz:76` | 38 | 7 | 3 |
| task_server_run_multishot | `projects/ritz/ritzlib/async_tasks.ritz:751` | 36 | 11 | 6 |
| buf_read_quoted | `projects/ritz/ritzlib/buf.ritz:318` | 36 | 13 | 4 |
| get_cache_path | `projects/ritz/ritzlib/meta.ritz:535` | 35 | 12 | 4 |
| json_emit_value | `projects/ritz/ritzlib/json.ritz:604` | 34 | 13 | 4 |
| args_print_help | `projects/ritz/ritzlib/args.ritz:370` | 33 | 13 | 5 |
| task_server_run | `projects/ritz/ritzlib/async_tasks.ritz:692` | 33 | 9 | 5 |
| iovec_append_int | `projects/ritz/ritzlib/iovec.ritz:154` | 33 | 7 | 3 |
| jp_parse_value | `projects/ritz/ritzlib/json.ritz:169` | 33 | 15 | 4 |
| lexer_handle_indent | `projects/ritz/ritzlib/lang/lexer.ritz:180` | 33 | 12 | 3 |
| parse_into | `projects/ritz/ritzlib/argspec.ritz:347` | 32 | 13 | 4 |
| test_malloc_small | `projects/ritz/ritzlib/tests/test_memory.ritz:437` | 32 | 1 | 1 |
| test_task_alloc | `projects/ritz/ritzlib/tests/test_async_server.ritz:54` | 30 | 6 | 2 |
| test_legacy_stat_getters_agree_with_struct | `projects/ritz/ritzlib/tests/test_fs_stat.ritz:145` | 30 | 12 | 2 |
| elf_parse_sections | `projects/ritz/ritzlib/elf.ritz:161` | 29 | 8 | 4 |

## Highest cyclomatic complexity (top 25)

| fn | where | CC | SLOC | depth |
|---|---|---|---|---|
| meta_free | `projects/ritz/ritzlib/meta.ritz:135` | 55 | 110 | 8 |
| args_parse | `projects/ritz/ritzlib/args.ritz:158` | 30 | 98 | 7 |
| test_byte_predicates | `projects/ritz/ritzlib/tests/test_buf.ritz:439` | 20 | 14 | 2 |
| jp_parse_string | `projects/ritz/ritzlib/json.ritz:219` | 17 | 60 | 5 |
| jp_parse_value | `projects/ritz/ritzlib/json.ritz:169` | 15 | 33 | 4 |
| test_dir_next_entry_yields_typed_entries | `projects/ritz/ritzlib/tests/test_fs_dirent.ritz:44` | 15 | 50 | 4 |
| args_print_help | `projects/ritz/ritzlib/args.ritz:370` | 13 | 33 | 5 |
| parse_into | `projects/ritz/ritzlib/argspec.ritz:347` | 13 | 32 | 4 |
| buf_read_quoted | `projects/ritz/ritzlib/buf.ritz:318` | 13 | 36 | 4 |
| jp_parse_object | `projects/ritz/ritzlib/json.ritz:381` | 13 | 71 | 4 |
| json_emit_value | `projects/ritz/ritzlib/json.ritz:604` | 13 | 34 | 4 |
| argspec_print_help | `projects/ritz/ritzlib/argspec.ritz:496` | 12 | 22 | 3 |
| lexer_handle_indent | `projects/ritz/ritzlib/lang/lexer.ritz:180` | 12 | 33 | 3 |
| get_cache_path | `projects/ritz/ritzlib/meta.ritz:535` | 12 | 35 | 4 |
| test_legacy_stat_getters_agree_with_struct | `projects/ritz/ritzlib/tests/test_fs_stat.ritz:145` | 12 | 30 | 2 |
| task_server_run_multishot | `projects/ritz/ritzlib/async_tasks.ritz:751` | 11 | 36 | 6 |
| strview_parse_i64 | `projects/ritz/ritzlib/strview.ritz:385` | 11 | 26 | 3 |
| buf_take_quoted | `projects/ritz/ritzlib/buf.ritz:248` | 10 | 22 | 4 |
| buf_read_while_alnum | `projects/ritz/ritzlib/buf.ritz:303` | 10 | 14 | 3 |
| jp_parse_number | `projects/ritz/ritzlib/json.ritz:289` | 10 | 28 | 4 |
| jp_parse_array | `projects/ritz/ritzlib/json.ritz:323` | 10 | 43 | 4 |
| get_size_class | `projects/ritz/ritzlib/memory.ritz:241` | 10 | 20 | 2 |
| socket_connect_timeout | `projects/ritz/ritzlib/net.ritz:408` | 10 | 38 | 2 |
| print_flag_help | `projects/ritz/ritzlib/argspec.ritz:476` | 9 | 18 | 3 |
| task_server_run | `projects/ritz/ritzlib/async_tasks.ritz:692` | 9 | 33 | 5 |

## Deepest nesting (top 25)

| fn | where | depth | SLOC |
|---|---|---|---|
| meta_free | `projects/ritz/ritzlib/meta.ritz:135` | 8 | 110 |
| args_parse | `projects/ritz/ritzlib/args.ritz:158` | 7 | 98 |
| task_server_run_multishot | `projects/ritz/ritzlib/async_tasks.ritz:751` | 6 | 36 |
| task_server_run_multishot | `projects/ritz/ritzlib/async/server.ritz:193` | 6 | 28 |
| block_on | `projects/ritz/ritzlib/async/executor.ritz:106` | 6 | 19 |
| async_block_on_i64 | `projects/ritz/ritzlib/async/executor.ritz:139` | 6 | 19 |
| jp_parse_string | `projects/ritz/ritzlib/json.ritz:219` | 5 | 60 |
| args_print_help | `projects/ritz/ritzlib/args.ritz:370` | 5 | 33 |
| task_server_run | `projects/ritz/ritzlib/async_tasks.ritz:692` | 5 | 33 |
| run_tasks | `projects/ritz/ritzlib/async/executor.ritz:48` | 5 | 27 |
| run_tasks | `projects/ritz/ritzlib/async_tasks.ritz:433` | 5 | 27 |
| task_server_run | `projects/ritz/ritzlib/async/server.ritz:148` | 5 | 25 |
| lexer_scan_string | `projects/ritz/ritzlib/lang/lexer.ritz:267` | 5 | 25 |
| tokendefs_get_name | `projects/ritz/ritzlib/lang/tokens.ritz:144` | 5 | 19 |
| build_want | `projects/ritz/ritzlib/tests/test_elf_output.ritz:124` | 5 | 19 |
| block_on | `projects/ritz/ritzlib/executor.ritz:87` | 5 | 17 |
| elf_find_test_functions | `projects/ritz/ritzlib/elf.ritz:267` | 5 | 12 |
| elf_print_test_functions | `projects/ritz/ritzlib/elf.ritz:289` | 5 | 11 |
| jp_parse_object | `projects/ritz/ritzlib/json.ritz:381` | 4 | 71 |
| test_dir_next_entry_yields_typed_entries | `projects/ritz/ritzlib/tests/test_fs_dirent.ritz:44` | 4 | 50 |
| jp_parse_array | `projects/ritz/ritzlib/json.ritz:323` | 4 | 43 |
| env_load | `projects/ritz/ritzlib/os/env.ritz:53` | 4 | 39 |
| buf_read_quoted | `projects/ritz/ritzlib/buf.ritz:318` | 4 | 36 |
| get_cache_path | `projects/ritz/ritzlib/meta.ritz:535` | 4 | 35 |
| json_emit_value | `projects/ritz/ritzlib/json.ritz:604` | 4 | 34 |

## Distribution

- functions > 100 SLOC: 1 (0.1%); > 300 SLOC: 0 (0.0%)
- CC > 20: 2 (0.1%); CC > 50: 1 (0.1%)
- nesting depth >= 6: 6 (0.4%)

## Files by size

| file | lines | SLOC | fns | dup-window lines |
|---|---|---|---|---|
| `projects/ritz/ritzlib/sys.ritz` | 1297 | 835 | 90 | 24 |
| `projects/ritz/ritzlib/tests/test_buf.ritz` | 718 | 586 | 49 | 0 |
| `projects/ritz/ritzlib/json.ritz` | 676 | 504 | 27 | 24 |
| `projects/ritz/ritzlib/meta.ritz` | 667 | 497 | 21 | 0 |
| `projects/ritz/ritzlib/uring.ritz` | 767 | 472 | 29 | 216 |
| `projects/ritz/ritzlib/tests/test_json.ritz` | 594 | 462 | 46 | 90 |
| `projects/ritz/ritzlib/tests/test_memory.ritz` | 668 | 424 | 37 | 12 |
| `projects/ritz/ritzlib/async_tasks.ritz` | 811 | 396 | 42 | 204 |
| `projects/ritz/ritzlib/buf.ritz` | 575 | 352 | 53 | 0 |
| `projects/ritz/ritzlib/argspec.ritz` | 517 | 350 | 42 | 0 |
| `projects/ritz/ritzlib/string.ritz` | 654 | 326 | 42 | 36 |
| `projects/ritz/ritzlib/fs.ritz` | 549 | 316 | 59 | 0 |
| `projects/ritz/ritzlib/strview.ritz` | 487 | 312 | 50 | 42 |
| `projects/ritz/ritzlib/net.ritz` | 551 | 298 | 56 | 6 |
| `projects/ritz/ritzlib/args.ritz` | 409 | 274 | 18 | 0 |
| `projects/ritz/ritzlib/tests/test_strview.ritz` | 408 | 271 | 34 | 12 |
| `projects/ritz/ritzlib/memory.ritz` | 428 | 240 | 25 | 0 |
| `projects/ritz/ritzlib/tests/test_string_io.ritz` | 277 | 237 | 28 | 0 |
| `projects/ritz/ritzlib/lang/lexer.ritz` | 346 | 235 | 20 | 0 |
| `projects/ritz/ritzlib/tests/test_string_methods.ritz` | 270 | 228 | 25 | 0 |
| `projects/ritz/ritzlib/process.ritz` | 453 | 222 | 19 | 12 |
| `projects/ritz/ritzlib/tests/test_argspec_parse.ritz` | 248 | 206 | 24 | 36 |
| `projects/ritz/ritzlib/span.ritz` | 334 | 202 | 43 | 42 |
| `projects/ritz/ritzlib/tests/test_meta.ritz` | 295 | 194 | 17 | 18 |
| `projects/ritz/ritzlib/hashmap.ritz` | 317 | 188 | 21 | 36 |

## String / C-idiom smell counts per file

| file | ptr_len_param_pair | fixed_u8_buffer | strlen_call | memcpy_call | memcmp_or_streq_call | manual_byte_copy | manual_byte_compare | char_code_compare | cstr_literal | malloc_cast | malloc_magic_size | i32_as_bool | total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `projects/ritz/ritzlib/tests/test_json.ritz` | 0 | 2 | 37 | 0 | 10 | 0 | 0 | 0 | 56 | 0 | 0 | 0 | 105 |
| `projects/ritz/ritzlib/tests/test_meta.ritz` | 0 | 3 | 12 | 0 | 26 | 0 | 0 | 0 | 52 | 0 | 0 | 0 | 93 |
| `projects/ritz/ritzlib/meta.ritz` | 1 | 0 | 1 | 1 | 6 | 0 | 0 | 0 | 37 | 11 | 1 | 1 | 59 |
| `projects/ritz/ritzlib/tests/test_strview.ritz` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 59 | 0 | 0 | 0 | 59 |
| `projects/ritz/ritzlib/tests/test_memory.ritz` | 0 | 21 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 26 | 0 | 55 |
| `projects/ritz/ritzlib/json.ritz` | 2 | 1 | 1 | 4 | 1 | 0 | 0 | 0 | 18 | 4 | 1 | 6 | 38 |
| `projects/ritz/ritzlib/sys.ritz` | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 26 |
| `projects/ritz/ritzlib/tests/test_args_output.ritz` | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 18 | 0 | 0 | 5 | 26 |
| `projects/ritz/ritzlib/tests/test_fs_iter.ritz` | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 18 | 0 | 0 | 4 | 24 |
| `projects/ritz/ritzlib/net.ritz` | 7 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 7 | 18 |
| `projects/ritz/ritzlib/span.ritz` | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 13 | 0 | 0 | 2 | 18 |
| `projects/ritz/ritzlib/args.ritz` | 0 | 1 | 0 | 0 | 4 | 0 | 0 | 0 | 7 | 0 | 0 | 5 | 17 |
| `projects/ritz/ritzlib/async_net.ritz` | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 14 |
| `projects/ritz/ritzlib/process.ritz` | 1 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 2 | 13 |
| `projects/ritz/ritzlib/tests/test_elf_output.ritz` | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 2 | 12 |
| `projects/ritz/ritzlib/tests/test_fs_dirent.ritz` | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 5 | 12 |
| `projects/ritz/ritzlib/fs.ritz` | 1 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 11 |
| `projects/ritz/ritzlib/testlib.ritz` | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 3 | 11 |
| `projects/ritz/ritzlib/iovec.ritz` | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 4 | 10 |
| `projects/ritz/ritzlib/str.ritz` | 0 | 1 | 2 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 10 |
| `projects/ritz/ritzlib/lang/tokens.ritz` | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 9 |
| `projects/ritz/ritzlib/tests/test_fs_stat.ritz` | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 9 |
| `projects/ritz/ritzlib/tests/test_process_env.ritz` | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 9 |
| `projects/ritz/ritzlib/async_tasks.ritz` | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 |
| `projects/ritz/ritzlib/executor.ritz` | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 |
| **total** | 60 | 95 | 62 | 15 | 58 | 0 | 0 | 0 | 347 | 18 | 28 | 137 | 820 |

## Duplicated 6-line windows (top 25 clusters by occurrences)

- **7×** `var g_out: [4096]u8` — `projects/ritz/ritzlib/tests/test_args_output.ritz:20`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:26`, `projects/ritz/ritzlib/tests/test_elf_output.ritz:25`, `projects/ritz/ritzlib/tests/test_env_output.ritz:14`, `projects/ritz/ritzlib/tests/test_iovec_output.ritz:20`, `projects/ritz/ritzlib/tests/test_timer_output.ritz:26`, `projects/ritz/ritzlib/tests/test_tokens_output.ritz:20`
- **7×** `fn read_all(fd: i32, buf: *u8, cap: i64) -> i64` — `projects/ritz/ritzlib/tests/test_args_output.ritz:25`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:31`, `projects/ritz/ritzlib/tests/test_elf_output.ritz:30`, `projects/ritz/ritzlib/tests/test_env_output.ritz:19`, `projects/ritz/ritzlib/tests/test_iovec_output.ritz:25`, `projects/ritz/ritzlib/tests/test_timer_output.ritz:31`, `projects/ritz/ritzlib/tests/test_tokens_output.ritz:25`
- **7×** `fn bytes_differ(buf: *u8, len: i64, want: StrView) -> i32` — `projects/ritz/ritzlib/tests/test_args_output.ritz:35`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:41`, `projects/ritz/ritzlib/tests/test_elf_output.ritz:40`, `projects/ritz/ritzlib/tests/test_env_output.ritz:29`, `projects/ritz/ritzlib/tests/test_iovec_output.ritz:35`, `projects/ritz/ritzlib/tests/test_timer_output.ritz:41`, `projects/ritz/ritzlib/tests/test_tokens_output.ritz:35`
- **7×** `0` — `projects/ritz/ritzlib/tests/test_args_output.ritz:43`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:49`, `projects/ritz/ritzlib/tests/test_elf_output.ritz:48`, `projects/ritz/ritzlib/tests/test_env_output.ritz:37`, `projects/ritz/ritzlib/tests/test_iovec_output.ritz:43`, `projects/ritz/ritzlib/tests/test_timer_output.ritz:49`, `projects/ritz/ritzlib/tests/test_tokens_output.ritz:43`
- **7×** `var o: [2]i32` — `projects/ritz/ritzlib/tests/test_args_output.ritz:48`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:54`, `projects/ritz/ritzlib/tests/test_elf_output.ritz:53`, `projects/ritz/ritzlib/tests/test_env_output.ritz:42`, `projects/ritz/ritzlib/tests/test_iovec_output.ritz:48`, `projects/ritz/ritzlib/tests/test_timer_output.ritz:54`, `projects/ritz/ritzlib/tests/test_tokens_output.ritz:48`
- **7×** `sys_dup2(o[1], 1)` — `projects/ritz/ritzlib/tests/test_args_output.ritz:54`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:60`, `projects/ritz/ritzlib/tests/test_elf_output.ritz:59`, `projects/ritz/ritzlib/tests/test_env_output.ritz:48`, `projects/ritz/ritzlib/tests/test_iovec_output.ritz:54`, `projects/ritz/ritzlib/tests/test_timer_output.ritz:60`, `projects/ritz/ritzlib/tests/test_tokens_output.ritz:54`
- **7×** `sys_dup2(e[1], 2)` — `projects/ritz/ritzlib/tests/test_args_output.ritz:55`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:61`, `projects/ritz/ritzlib/tests/test_elf_output.ritz:60`, `projects/ritz/ritzlib/tests/test_env_output.ritz:49`, `projects/ritz/ritzlib/tests/test_iovec_output.ritz:55`, `projects/ritz/ritzlib/tests/test_timer_output.ritz:61`, `projects/ritz/ritzlib/tests/test_tokens_output.ritz:55`
- **7×** `sys_exit(run_body(which))` — `projects/ritz/ritzlib/tests/test_args_output.ritz:60`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:66`, `projects/ritz/ritzlib/tests/test_elf_output.ritz:65`, `projects/ritz/ritzlib/tests/test_env_output.ritz:54`, `projects/ritz/ritzlib/tests/test_iovec_output.ritz:60`, `projects/ritz/ritzlib/tests/test_timer_output.ritz:66`, `projects/ritz/ritzlib/tests/test_tokens_output.ritz:60`
- **7×** `sys_close(e[0])` — `projects/ritz/ritzlib/tests/test_args_output.ritz:66`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:72`, `projects/ritz/ritzlib/tests/test_elf_output.ritz:71`, `projects/ritz/ritzlib/tests/test_env_output.ritz:60`, `projects/ritz/ritzlib/tests/test_iovec_output.ritz:66`, `projects/ritz/ritzlib/tests/test_timer_output.ritz:72`, `projects/ritz/ritzlib/tests/test_tokens_output.ritz:66`
- **7×** `sqe.rw_flags = 0` — `projects/ritz/ritzlib/uring.ritz:349`, `projects/ritz/ritzlib/uring.ritz:366`, `projects/ritz/ritzlib/uring.ritz:400`, `projects/ritz/ritzlib/uring.ritz:454`, `projects/ritz/ritzlib/uring.ritz:560`, `projects/ritz/ritzlib/uring.ritz:578`, `projects/ritz/ritzlib/uring.ritz:656`
- **6×** `if exec.waker_io_result != 0` — `projects/ritz/ritzlib/executor.ritz:157`, `projects/ritz/ritzlib/executor.ritz:180`, `projects/ritz/ritzlib/executor.ritz:199`, `projects/ritz/ritzlib/executor.ritz:219`, `projects/ritz/ritzlib/executor.ritz:239`, `projects/ritz/ritzlib/executor.ritz:259`
- **6×** `let result: i32 = exec.waker_io_result` — `projects/ritz/ritzlib/executor.ritz:158`, `projects/ritz/ritzlib/executor.ritz:181`, `projects/ritz/ritzlib/executor.ritz:200`, `projects/ritz/ritzlib/executor.ritz:220`, `projects/ritz/ritzlib/executor.ritz:240`, `projects/ritz/ritzlib/executor.ritz:260`
- **6×** `var status: i32 = 0` — `projects/ritz/ritzlib/tests/test_args_output.ritz:67`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:73`, `projects/ritz/ritzlib/tests/test_elf_output.ritz:72`, `projects/ritz/ritzlib/tests/test_env_output.ritz:61`, `projects/ritz/ritzlib/tests/test_iovec_output.ritz:67`, `projects/ritz/ritzlib/tests/test_tokens_output.ritz:67`
- **6×** `sqe.rw_flags = flags` — `projects/ritz/ritzlib/uring.ritz:383`, `projects/ritz/ritzlib/uring.ritz:418`, `projects/ritz/ritzlib/uring.ritz:436`, `projects/ritz/ritzlib/uring.ritz:602`, `projects/ritz/ritzlib/uring.ritz:698`, `projects/ritz/ritzlib/uring.ritz:718`
- **5×** `fn demo_spec() -> ArgSpec` — `projects/ritz/ritzlib/tests/test_argspec_argv.ritz:24`, `projects/ritz/ritzlib/tests/test_argspec_errors.ritz:24`, `projects/ritz/ritzlib/tests/test_argspec_int.ritz:24`, `projects/ritz/ritzlib/tests/test_argspec_output.ritz:87`, `projects/ritz/ritzlib/tests/test_argspec_parse.ritz:24`
- **4×** `task_server_poll_tasks(srv)` — `projects/ritz/ritzlib/async/server.ritz:157`, `projects/ritz/ritzlib/async/server.ritz:202`, `projects/ritz/ritzlib/async_tasks.ritz:714`, `projects/ritz/ritzlib/async_tasks.ritz:773`
- **4×** `let wait_ret = uring_submit_and_wait(@srv.ring, 1)` — `projects/ritz/ritzlib/async/server.ritz:160`, `projects/ritz/ritzlib/async/server.ritz:205`, `projects/ritz/ritzlib/async_tasks.ritz:717`, `projects/ritz/ritzlib/async_tasks.ritz:776`
- **4×** `uring_sqe_submit(@rt.ring)` — `projects/ritz/ritzlib/async_net.ritz:244`, `projects/ritz/ritzlib/async_net.ritz:270`, `projects/ritz/ritzlib/async_runtime.ritz:73`, `projects/ritz/ritzlib/async_runtime.ritz:100`
- **4×** `let cqe: *IoUringCqe = uring_peek_cqe(@rt.ring)` — `projects/ritz/ritzlib/async_net.ritz:250`, `projects/ritz/ritzlib/async_net.ritz:276`, `projects/ritz/ritzlib/async_runtime.ritz:81`, `projects/ritz/ritzlib/async_runtime.ritz:106`
- **4×** `var pos: i64 = 0` — `projects/ritz/ritzlib/span.ritz:150`, `projects/ritz/ritzlib/span.ritz:190`, `projects/ritz/ritzlib/strview.ritz:258`, `projects/ritz/ritzlib/strview.ritz:279`
- **4×** `while pos < max_pos` — `projects/ritz/ritzlib/span.ritz:152`, `projects/ritz/ritzlib/span.ritz:192`, `projects/ritz/ritzlib/strview.ritz:260`, `projects/ritz/ritzlib/strview.ritz:281`
- **4×** `import ritzlib.argspec` — `projects/ritz/ritzlib/tests/test_argspec_argv.ritz:17`, `projects/ritz/ritzlib/tests/test_argspec_errors.ritz:17`, `projects/ritz/ritzlib/tests/test_argspec_int.ritz:17`, `projects/ritz/ritzlib/tests/test_argspec_parse.ritz:17`
- **4×** `var spec = argspec_new("demo", "A demo program")` — `projects/ritz/ritzlib/tests/test_argspec_argv.ritz:25`, `projects/ritz/ritzlib/tests/test_argspec_errors.ritz:25`, `projects/ritz/ritzlib/tests/test_argspec_int.ritz:25`, `projects/ritz/ritzlib/tests/test_argspec_parse.ritz:25`
- **4×** `let input = c"true"` — `projects/ritz/ritzlib/tests/test_json.ritz:446`, `projects/ritz/ritzlib/tests/test_json.ritz:459`, `projects/ritz/ritzlib/tests/test_json.ritz:472`, `projects/ritz/ritzlib/tests/test_json.ritz:485`
- **4×** `sqe.off = 0` — `projects/ritz/ritzlib/uring.ritz:415`, `projects/ritz/ritzlib/uring.ritz:433`, `projects/ritz/ritzlib/uring.ritz:695`, `projects/ritz/ritzlib/uring.ritz:715`

Total duplicate clusters: 95
