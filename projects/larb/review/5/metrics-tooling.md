<!-- Generated 2026-11-16 at main 6f245b93 (git archive), same paths as review/4:
     ritz_metrics.py rz projects/ritz/{build,cache,packaging}.py projects/ritz/tools --lang py --top 20 -->
# ritz-metrics: 67 files, 19755 SLOC, 1428 functions

## Longest functions (top 20)

| fn | where | SLOC | CC | depth |
|---|---|---|---|---|
| suite_stack | `projects/ritz/tools/smoke_stack.py:913` | 359 | 110 | 11 |
| compile_freestanding_binary | `projects/ritz/build.py:2060` | 279 | 74 | 9 |
| suite_mausoleum | `projects/ritz/tools/smoke_stack.py:639` | 180 | 43 | 7 |
| build_package | `projects/ritz/build.py:2516` | 153 | 35 | 7 |
| apply_migration | `projects/ritz/tools/apply_string_migration.py:266` | 146 | 44 | 5 |
| run_pipeline | `rz:1412` | 125 | 37 | 5 |
| compile_binary | `projects/ritz/build.py:1722` | 124 | 41 | 5 |
| _generate_alternative | `projects/ritz/tools/ritzgen_py/ritz_generator.py:568` | 119 | 38 | 6 |
| plan_binaries | `projects/ritz/build.py:1265` | 114 | 30 | 6 |
| main | `projects/ritz/tools/run_regression_matrix.py:719` | 109 | 43 | 6 |
| main | `projects/ritz/tools/ci_local.py:289` | 108 | 38 | 6 |
| install_package | `projects/ritz/packaging.py:617` | 96 | 25 | 4 |
| cmd_compare | `rz:1089` | 90 | 30 | 4 |
| test_projects_parallel | `rz:591` | 89 | 26 | 8 |
| cmd_ci_run | `rz:1603` | 81 | 19 | 4 |
| compile_modules | `projects/ritz/build.py:1594` | 81 | 24 | 7 |
| main | `projects/ritz/build.py:3599` | 79 | 1 | 9 |
| build_parser | `rz:1851` | 71 | 3 | 7 |
| _prefix_from_call | `projects/ritz/tools/audit_string_literals.py:236` | 71 | 27 | 4 |
| generate_tokens | `projects/ritz/tools/ritzgen_py/ritz_generator.py:152` | 70 | 12 | 4 |

## Highest cyclomatic complexity (top 20)

| fn | where | CC | SLOC | depth |
|---|---|---|---|---|
| suite_stack | `projects/ritz/tools/smoke_stack.py:913` | 110 | 359 | 11 |
| compile_freestanding_binary | `projects/ritz/build.py:2060` | 74 | 279 | 9 |
| apply_migration | `projects/ritz/tools/apply_string_migration.py:266` | 44 | 146 | 5 |
| main | `projects/ritz/tools/run_regression_matrix.py:719` | 43 | 109 | 6 |
| suite_mausoleum | `projects/ritz/tools/smoke_stack.py:639` | 43 | 180 | 7 |
| compile_binary | `projects/ritz/build.py:1722` | 41 | 124 | 5 |
| main | `projects/ritz/tools/ci_local.py:289` | 38 | 108 | 6 |
| _generate_alternative | `projects/ritz/tools/ritzgen_py/ritz_generator.py:568` | 38 | 119 | 6 |
| run_pipeline | `rz:1412` | 37 | 125 | 5 |
| build_package | `projects/ritz/build.py:2516` | 35 | 153 | 7 |
| cmd_compare | `rz:1089` | 30 | 90 | 4 |
| plan_binaries | `projects/ritz/build.py:1265` | 30 | 114 | 6 |
| _prefix_from_call | `projects/ritz/tools/audit_string_literals.py:236` | 27 | 71 | 4 |
| test_projects_parallel | `rz:591` | 26 | 89 | 8 |
| discover_sources | `projects/ritz/build.py:810` | 26 | 55 | 5 |
| install_package | `projects/ritz/packaging.py:617` | 25 | 96 | 4 |
| compile_modules | `projects/ritz/build.py:1594` | 24 | 81 | 7 |
| run_test_file | `projects/ritz/build.py:2973` | 22 | 51 | 4 |
| compile_library | `projects/ritz/build.py:1979` | 21 | 65 | 5 |
| cmd_test | `projects/ritz/build.py:3294` | 21 | 63 | 7 |

## Deepest nesting (top 20)

| fn | where | depth | SLOC |
|---|---|---|---|
| test_in_process_unit_runs_in_the_package_with_the_test_env | `projects/ritz/tools/test_cas_harness_and_inprocess_units.py:300` | 16 | 19 |
| test_memo_entries_are_gc_able_store_objects_and_not_counted | `projects/ritz/tools/test_closure_key_memo.py:219` | 16 | 10 |
| test_ritzunit_sources_without_the_memo_resolve_every_time | `projects/ritz/tools/test_closure_key_memo.py:287` | 15 | 8 |
| test_the_memo_is_keyed_on_everything_but_the_closure | `projects/ritz/tools/test_closure_key_memo.py:167` | 14 | 21 |
| test_a_deleted_closure_file_is_a_memo_miss | `projects/ritz/tools/test_closure_key_memo.py:153` | 14 | 7 |
| test_passing_o2_compile_succeeds_with_zero_failures | `projects/ritz/tools/test_build_clang_obj_bounded.py:183` | 14 | 6 |
| test_o2_timeout_fires_and_kills_the_process_group | `projects/ritz/tools/test_build_clang_obj_bounded.py:230` | 13 | 29 |
| test_in_process_verdicts_match_the_subprocess_ones | `projects/ritz/tools/test_cas_harness_and_inprocess_units.py:280` | 13 | 15 |
| test_a_harness_that_does_not_compile_is_not_stored | `projects/ritz/tools/test_cas_harness_and_inprocess_units.py:218` | 13 | 13 |
| test_lowest_sched_runs_first_including_follow_ups | `projects/ritz/tools/test_rz_parallel.py:133` | 13 | 13 |
| _buildpy | `rz:516` | 13 | 12 |
| test_failed_builds_reach_the_stats_log_and_the_summary | `projects/ritz/tools/test_cas_failed_and_freestanding.py:70` | 13 | 12 |
| test_failing_o2_compile_fails_the_build_loudly | `projects/ritz/tools/test_build_clang_obj_bounded.py:192` | 12 | 14 |
| test_discovery_sorted_and_test_only_root_files | `projects/ritz/tools/test_rz_parallel.py:451` | 12 | 12 |
| buildpy | `projects/ritz/tools/test_cas_failed_and_freestanding.py:130` | 12 | 7 |
| suite_stack | `projects/ritz/tools/smoke_stack.py:913` | 11 | 359 |
| test_build_units_in_order_and_failed_set | `projects/ritz/tools/test_rz_parallel.py:412` | 11 | 15 |
| test_o2_compile_is_address_space_capped | `projects/ritz/tools/test_build_clang_obj_bounded.py:267` | 11 | 11 |
| zeus_alone | `projects/ritz/tools/smoke_stack.py:1204` | 10 | 19 |
| test_plan_build_failure_runs_nothing | `projects/ritz/tools/test_rz_parallel.py:551` | 10 | 17 |

## Distribution

- functions > 100 SLOC: 11 (0.8%); > 300 SLOC: 1 (0.1%)
- CC > 20: 21 (1.5%); CC > 50: 2 (0.1%)
- nesting depth >= 6: 108 (7.6%)

## Files by size

| file | lines | SLOC | fns | dup-window lines |
|---|---|---|---|---|
| `projects/ritz/build.py` | 3714 | 2568 | 105 | 108 |
| `rz` | 1957 | 1482 | 67 | 48 |
| `projects/ritz/tools/smoke_stack.py` | 1599 | 1263 | 110 | 0 |
| `projects/ritz/tools/ritzgen_py/ritz_generator.py` | 983 | 726 | 27 | 252 |
| `projects/ritz/cache.py` | 1063 | 719 | 49 | 0 |
| `projects/ritz/tools/run_regression_matrix.py` | 845 | 640 | 32 | 0 |
| `projects/ritz/packaging.py` | 902 | 624 | 32 | 0 |
| `projects/ritz/tools/test_rz_parallel.py` | 629 | 489 | 56 | 48 |
| `projects/ritz/tools/test_apply_string_migration.py` | 575 | 471 | 28 | 102 |
| `projects/ritz/tools/check_doc_examples.py` | 555 | 433 | 16 | 0 |
| `projects/ritz/tools/test_host_budget.py` | 554 | 417 | 30 | 0 |
| `projects/ritz/tools/test_ci_local.py` | 540 | 380 | 47 | 0 |
| `projects/ritz/tools/audit_string_literals.py` | 540 | 368 | 10 | 0 |
| `projects/ritz/tools/test_cas.py` | 460 | 361 | 33 | 48 |
| `projects/ritz/tools/apply_string_migration.py` | 485 | 353 | 13 | 0 |
| `projects/ritz/tools/test_run_regression_matrix_gate.py` | 457 | 341 | 40 | 0 |
| `projects/ritz/tools/ritz-lint/ritz_lint.py` | 472 | 329 | 4 | 0 |
| `projects/ritz/tools/ci_local.py` | 415 | 325 | 15 | 0 |
| `projects/ritz/tools/ritzgen_py/grammar_parser.py` | 424 | 324 | 12 | 12 |
| `projects/ritz/tools/test_cas_gc_race.py` | 364 | 291 | 23 | 36 |

## String / C-idiom smell counts per file

| file | bare_except | subprocess_shell_true | global_stmt | total |
|---|---|---|---|---|
| `projects/ritz/build.py` | 0 | 0 | 4 | 4 |
| `rz` | 0 | 1 | 1 | 2 |
| `projects/ritz/tools/ci_local.py` | 0 | 0 | 1 | 1 |
| `projects/ritz/tools/ritz-lint/ritz_lint.py` | 1 | 0 | 0 | 1 |
| `projects/ritz/tools/run_regression_matrix.py` | 0 | 0 | 1 | 1 |
| `projects/ritz/tools/test_check_test_tempdirs.py` | 0 | 0 | 1 | 1 |
| **total** | 1 | 1 | 8 | 10 |

## Duplicated 6-line windows (top 20 clusters by occurrences)

- **23×** `self._emit('')` — `projects/ritz/tools/ritzgen_py/ritz_generator.py:210`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:216`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:222`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:228`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:261`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:267`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:348`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:391` (+15 more)
- **8×** `buf = io.StringIO()` — `projects/ritz/tools/test_apply_string_migration.py:223`, `projects/ritz/tools/test_apply_string_migration.py:255`, `projects/ritz/tools/test_apply_string_migration.py:326`, `projects/ritz/tools/test_apply_string_migration.py:353`, `projects/ritz/tools/test_apply_string_migration.py:390`, `projects/ritz/tools/test_apply_string_migration.py:422`, `projects/ritz/tools/test_apply_string_migration.py:499`, `projects/ritz/tools/test_apply_string_migration.py:562`
- **7×** `)` — `projects/ritz/tools/test_apply_string_migration.py:221`, `projects/ritz/tools/test_apply_string_migration.py:253`, `projects/ritz/tools/test_apply_string_migration.py:325`, `projects/ritz/tools/test_apply_string_migration.py:389`, `projects/ritz/tools/test_apply_string_migration.py:421`, `projects/ritz/tools/test_apply_string_migration.py:498`, `projects/ritz/tools/test_apply_string_migration.py:561`
- **5×** `self._reset()` — `projects/ritz/tools/ritzgen_py/ritz_generator.py:154`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:260`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:347`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:779`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:833`
- **5×** `from pathlib import Path` — `projects/ritz/tools/test_cas.py:23`, `projects/ritz/tools/test_cas_gc_race.py:25`, `projects/ritz/tools/test_cas_harness_and_inprocess_units.py:27`, `projects/ritz/tools/test_cas_singleflight.py:24`, `projects/ritz/tools/test_closure_key_memo.py:19`
- **5×** `import pytest` — `projects/ritz/tools/test_cas.py:25`, `projects/ritz/tools/test_cas_gc_race.py:27`, `projects/ritz/tools/test_cas_harness_and_inprocess_units.py:29`, `projects/ritz/tools/test_cas_singleflight.py:26`, `projects/ritz/tools/test_closure_key_memo.py:21`
- **4×** `"""Generate tokens.ritz with constants and Token struct."""` — `projects/ritz/tools/ritzgen_py/ritz_generator.py:153`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:346`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:778`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:832`
- **4×** `@pytest.fixture` — `projects/ritz/tools/test_build_clang_obj_bounded.py:91`, `projects/ritz/tools/test_build_clean.py:39`, `projects/ritz/tools/test_build_freestanding_compiler.py:55`, `projects/ritz/tools/test_build_test_compiler.py:35`
- **4×** `def buildpy(request):` — `projects/ritz/tools/test_build_clang_obj_bounded.py:92`, `projects/ritz/tools/test_build_clean.py:40`, `projects/ritz/tools/test_build_freestanding_compiler.py:56`, `projects/ritz/tools/test_build_test_compiler.py:36`
- **4×** `RITZ0_DIR = PKG_DIR / "ritz0"` — `projects/ritz/tools/test_cas.py:28`, `projects/ritz/tools/test_cas_gc_race.py:30`, `projects/ritz/tools/test_cas_harness_and_inprocess_units.py:32`, `projects/ritz/tools/test_cas_singleflight.py:29`
- **4×** `root = tmp_path / "cas"` — `projects/ritz/tools/test_cas.py:43`, `projects/ritz/tools/test_cas_gc_race.py:43`, `projects/ritz/tools/test_cas_harness_and_inprocess_units.py:48`, `projects/ritz/tools/test_cas_singleflight.py:43`
- **3×** `self._emit(f'const TOK_{name}: i32 = {tid}')` — `projects/ritz/tools/ritzgen_py/ritz_generator.py:209`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:818`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:888`
- **3×** `self._emit('        line: line as i32,')` — `projects/ritz/tools/ritzgen_py/ritz_generator.py:232`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:819`, `projects/ritz/tools/ritzgen_py/ritz_generator.py:893`
- **3×** `@pytest.fixture(autouse=True)` — `projects/ritz/tools/test_cas.py:40`, `projects/ritz/tools/test_cas_harness_and_inprocess_units.py:45`, `projects/ritz/tools/test_closure_key_memo.py:37`
- **3×** `KEY = "7c" + "b" * 62` — `projects/ritz/tools/test_cas_failed_and_freestanding.py:38`, `projects/ritz/tools/test_cas_gc_race.py:38`, `projects/ritz/tools/test_cas_singleflight.py:38`
- **2×** `try:` — `projects/ritz/build.py:662`, `projects/ritz/build.py:795`
- **2×** `result = subprocess.run(compile_cmd, capture_output=True, text=True, env=env)` — `projects/ritz/build.py:1651`, `projects/ritz/build.py:2257`
- **2×** `if cas_key is None:` — `projects/ritz/build.py:1677`, `projects/ritz/build.py:2274`
- **2×** `def build_fn(compile_src=compile_src, ll_path=ll_path, obj_path=obj_path):` — `projects/ritz/build.py:1680`, `projects/ritz/build.py:2277`
- **2×** `failure = None` — `projects/ritz/build.py:1693`, `projects/ritz/build.py:2289`

Total duplicate clusters: 47
