# LARB v5 Review: ritz1 (self-hosted compiler)

**Reviewed:** 2026-11-16 · **Baseline:** review/4 (2026-10-25) · **Status:** CRITICAL

**Method:** `INSTRUCTIONS_v4.md`, read-only, on main @ `6f245b93` (no ritz1 source changes since). Metrics: [metrics-ritz1.md](metrics-ritz1.md), from
`ritz_metrics.py projects/ritz/ritz1/src --top 30`, the same path and flags as review/4. The baseline
was re-measured from `git archive 30815afa`, and it reproduces review/4 exactly (23 files, 25,838 SLOC, 763 fns).
Threshold counts below come from both JSON dumps. Repros used the existing `projects/ritz/ritz1/build/ritz1` binary
(built 2026-11-16 00:55, after `6f245b93`) and `ritz0.py`, single files in `/tmp/r5`. AGAST was not consulted. Status
comes from code, commits and repros only.

## Summary

The correctness tickets landed and hold up in code and repros:
- capacity drops fixed (#1813);
- the `[N]u16` layout bug fixed (#1814);
- the stale workarounds deleted (#1815);
- the cache checks import hashes (#1807);
- `format_into` and ritz1 `asm` added (#1824, #1825).

The structure got worse, and fast. In three weeks ritz1 grew from 25.8k to 56.6k SLOC (×2.2) and from 763 to 2,515 functions. Six
hand-written files now exceed the 3,000-SLOC Critical threshold (there were 0). The import cycle grew from 7 to 25
modules, and it now includes `emitter_core` and `monomorph`. That happened because six new checker modules
(ownership, ref, let, bool, call, must_use), plus six type-fact helpers, were built *on `EmitterState` and called during emission*. The v4 design
findings (no semantic phase, IR by string concatenation, C idioms, decomposition) are all **REGRESSED** by the
metrics. They were not touched. Status stays **CRITICAL**: the bugs were fixed, but the architecture debt behind them roughly doubled.

## Against review/4

| id | title | v4 sev | now | evidence | ticket |
|---|---|---|---|---|---|
| F1 | Silent data loss at fixed capacities / unhandled kinds | Critical | **FIXED** | `b8e786c0`. Enum table is now growable (`ast_helpers.ritz:6638-6655`). Call args use heap `call_reg_slots` (`emitter_expr_call.ritz:798,4538`). `add_local_full` reallocs (`emitter_core.ritz:1373-1376`), and so does `add_instantiation` (`monomorph.ritz:91-99`). `STMT_MEMBER_INDEX_ASSIGN` is lowered (`emitter_stmt.ritz:6759`), and the default arm errors (`:6809`). `find_*` falls back to a list scan on hash collision (`emitter_core.ritz:1438-1471`). Tab repro: one located error `tab.ritz:2:1: Tabs not allowed`, exits. Indent push bounded (`lexer_nfa.ritz:600`). A new silent cap appeared in `6f245b93`, see N7 | #1813 |
| F2 | Eleven type tables that disagree | Critical | **PARTLY** | `40cbd8fc`. Repro `struct S {a:[4]u16, b:i64}` → `%S = type {[4 x i16], i64}`. Mixed `bool/f32/u16/[3]u32` gives `sizeof` 24, which is correct. Still no single type representation: 0 `TypeRef`. There are 12 type→LLVM emitters (`emit_llvm_type`, `emit_field_llvm_type`, `emit_param_llvm_type`, `emit_fn_ret_llvm_type`, `emit_local_array_llvm_type`, `emit_array_value_llvm_type`, `emit_array_field_llvm_type`, `emit_global_llvm_type`, `emit_extern_global_llvm_type`, `asm_llvm_type`, `emit_float_llvm_ty`, `neg_float_llvm_type`). Size/align is spread over 8 helpers in `emitter_core` plus 17 `sizeof_*` in `emitter_expr_call`. `Parser` `last_*` side channels went 15 → 20 | #1814 |
| F3 | No semantic phase | Critical | **REGRESSED** | Gains: pre-emission passes now exist (`main.ritz:1288-1314`: impls, binder, reachability, generic inference), and calls are arity-checked (`call_check.ritz:132`). Regressions: all other checks run inside emission (N1). `get_expr_type` went CC 53 → 103 and 22 → 47 references (`emitter_core.ritz:5861`). `emit_var_decl` → `emit_var_decl_at` went 452/217 → 764 SLOC / **CC 339** (`emitter_stmt.ritz:1233`). 56 unlocated `emit_ir_error` sites remain (`emitter_core.ritz:602-609`) | #1816 |
| F4 | IR built by string concatenation | Major | **REGRESSED** (gap part FIXED) | `c"..."` literals 3,700 → 5,979; `next_reg(` 561 → 738; `emit_str(` 3,226 → 4,413; `emit_reg(` 1,353 → 1,767. The `= trunc i64` ladder is 17× (was 19×). Passes that re-parse IR text went from 2 to **4**: `align_packed_accesses` (`emitter.ritz:637`) and `own_end_fn` are new. `own_end_fn` re-scans the body for `"  ret "` lines to insert drop glue (`ownership.ritz:3490-3525`). `format_into` exists (`aa407393`) but ritz1 itself never uses it to build IR (0 uses outside `emitter_print` comments) | #1817, #1824 |
| F5 | Decomposition and layering | Major | **REGRESSED** | Fns >300 SLOC 12 → 15; >150 SLOC 25 → 33. The import SCC went from **7 to 25 modules** (both graphs re-derived). `emitter_core` imports `ownership`, `ref_check`, `deref_field` (`emitter_core.ritz:19-21`). `monomorph` and `reachability` import `emitter_core` (`monomorph.ritz:17`, `reachability.ritz`). `EmitterState` fields 46 → 82. `emitter_print`→`interp`→`parser_gen` is unchanged. The depth-18 `__builtin_alloca` char ladder is still there (`emitter_expr_call.ritz:4262-4271`) | #1818 |
| F6 | Generated parser bloated; 14 assign special cases | Major | **OPEN** | `parse_assign_stmt` 683 → 635 SLOC, CC 210. The grammar `assign_stmt` still has 16 alternatives (`grammars/ritz1.grammar:1042`). `grammars/ritz.grammar` is still tracked, with 0 commits since v4. The `Makefile:248` "ast_helpers ... diverged by design" comment is unchanged. FIRST-set dispatch and rollback were not re-verified | #1819 |
| F7 | C in Ritz clothing | Major | **REGRESSED** | `(*u8,len)` pairs 240 → 640; `i32_as_bool` 389 → 1,185; memcmp/streq 206 → 470; module `var`s 40 → 206. Still 0 `enum`, 0 `match`, 0 `impl`. `name_eq(` 167 → 410; all 5 hand-rolled compare helpers remain (`emitter_core.ritz:1854`, `ast_helpers.ritz:100`, `emitter_expr_call.ritz:104`, `ll_copy_scan.ritz:11,20`). Numeric ASCII compares ~234 → ~326. Wins: `[MONOMORPH]` stderr lines are gone, and magic `parser_alloc(p, N)` went 30 → 12 | #1820 |
| F8 | Compiler works around its own miscompiles | Major | **FIXED** | `3950f7c2` fixed the `**T` deref stride, deleted 5 workarounds, and added the matrix test `ritz0/test/test_issue_ritz1_src_workarounds.ritz` | #1815 |
| F9 | Runtime NFA lexer | Minor | **OPEN** | `lexer_next_token` CC 98 → 105, depth 14 (`lexer_nfa.ritz:660`). Runtime `[4096]i32` tables are still built (`main.ritz:115-116`). "workaround for NFA negation bug" (`lexer_nfa.ritz:728`) | #1821 |
| F10 | Cache fast path ignores imports | Critical | **FIXED** | `8d2b27db`: `check_source_unchanged` requires `sig_deps_unchanged` (`fn_cache.ritz:1011-1012`). No uncalled `fn_cache` functions | #1807 |
| F11 | Enums not in the AST | Major | **PARTLY** | ritz1 now has single-payload and struct variants. Repro `Circle(i64)/Sq(i64)` + `match` → exit 12, correct. But `Module` still has no enum list (`ast.ritz`, struct `Module`), and `enum_def_skip` returns 0 (`ast_helpers.ritz:6564`). Variants are still global parallel arrays, and `Option`/`Result` are still special-cased by name (`monomorph.ritz:215-218,722,826`). Multi-field tuple variants don't parse (N4) | #1295 |
| — | Stale ritz1 docs | — | **OPEN** | `ritz1/ARCHITECTURE.md:8` says "11 source files, ~13,700 lines" (now 41 / 76,068). `SELF_HOSTING_PLAN.md:14` says for-loops are "Not implemented". Neither has been touched since April/February | #1827 |
| — | Lang: format into `String` | — | **FIXED** | `aa407393` (spec + ritz0 + ritz1) | #1824 |
| — | Lang: inline `asm` | — | **PARTLY** | ritz1 parses and lowers asm (`0568dff7`, `bb6af962`, `emitter_asm.ritz`). The syscall shims are still hand-emitted text in the compiler: 28 `weak_odr` defs at `emitter.ritz:1608+`, and that dup cluster went 33× → 43× | #1825 |

## Metrics delta

| metric | review/4 | now |
|---|---|---|
| files / lines / SLOC / functions | 23 / 35,018 / 25,838 / 763 | **41 / 76,068 / 56,636 / 2,515** |
| fns SLOC >150 (Major) / >300 (Critical) | 25 / 12 | 33 / 15 |
| fns CC >30 / >80 | 40 / 16 | 71 / 18 |
| fns depth ≥6 / ≥9 | 34 / 8 | 50 / 7 |
| hand-written files SLOC >1500 / >3000 | 5 / 0 | **12 / 6** |
| top fn SLOC | `emit_expr_index` 885 | `emit_stmt_inner` 786 (`emit_expr_index` 705) |
| top fn CC | `emit_expr_index` 299 | `emit_var_decl_at` **339** |
| max depth | 18 (`emit_expr_call`) | 18 (same) |
| dup clusters total / ≥3 / ≥8 | 400 / 109 / 12 | 562 / 180 / 22 |
| largest dup cluster | 33× syscall shim | 43× syscall shim |
| import SCC | 7 modules | 25 modules |
| `EmitterState` / `LocalVar` / `Stmt` / `Parser` fields | 46 / 11 / 31 / 27 | 82 / 39 / 49 / 35 |
| smells: ptr_len_pair / i32_as_bool / cstr_literal / memcmp-streq / memcpy / strlen / malloc_cast / fixed_u8_buf | 240 / 389 / 3,700 / 206 / 14 / 3 / 45 / 20 | 640 / 1,185 / 5,979 / 470 / 64 / 26 / 27 / 14 |
| `enum` / `match` / `impl` / `bool` sites in ritz1 | 0 / 0 / 0 / 9 | 0 / 0 / 0 / 29 |

Six files are over 3,000 SLOC (the Critical threshold): `emitter_expr_call` 5,555, `ast_helpers` 5,400, `emitter_stmt` 5,007,
`emitter_core` 4,127, `monomorph` 3,105, `ownership` 3,024. `parser_gen` (8,137) is generated and excluded. The share of
functions over threshold fell only because many small helpers were added. Every absolute count rose.

## New findings

### N1. Semantic checks were built inside the emitter [architecture] — Critical
- Evidence:
  - **Where they run:** every public entry point of `ownership`, `ref_check`, `let_check`, `bool_check`, `call_check` and `must_use` takes `s: *EmitterState`, and the emitter calls them mid-lowering. Examples: `own_check_stmt` (`ownership.ritz:2817`), `ref_check_stmt` (`ref_check.ritz:1460`), `let_check_stmt` (`let_check.ritz:488`), `call_check_arity` (`call_check.ritz:132`), `bool_check_cond` (`bool_check.ritz:379`), `must_use_check` (`must_use.ritz:31`).
  - **Size:** together with `deref_field`, `index_through`, `literal_slot`, `float_slot`, `enum_as_int` and `tail_value`, that is 8,113 SLOC of checking and type facts living in the codegen layer.
  - **Layering:** `emitter_core` imports `ownership`, `ref_check` and `deref_field` (`emitter_core.ritz:19-21`). This is what grew the import cycle from 7 to 25 modules.
  - **Drop glue:** ownership inserts drops by rewriting emitted IR text (`ownership.ritz:3490-3525`).
- Impact: a check can only run if codegen reaches the node. Checks cannot be shared with ritz0's rule modules (`ritz0/*_rules.py`, which are AST passes). The planned sema phase (#1816) now has to extract 7 modules instead of starting fresh.
- Fix direction: move `*_check` and `ownership` onto a `Sema` context over the AST, run them between `infer_generic_calls` and `emit_module` (`main.ritz:1310-1320`), and pass results down as typed annotations. Freeze this pattern: no new `pub fn *_check*(s: *EmitterState …)`. The grep must stay empty for new modules.
- Ticket: #1816 (existing)

### N2. Six hand-written files past the Critical file threshold; size doubled in 3 weeks [architecture] — Critical
- Evidence: the Metrics delta above. 913 commits touched ritz1 between `30815afa` and `6f245b93`, nearly all one-shape parity fixes ("ritz1 types X as ritz0 does"). Examples: `4490fbf9`, `3d483713`, `254833ac`.
- Impact: each parity fix adds a branch to `emit_var_decl_at` / `get_expr_type` / `emit_expr_method` (CC 339 / 103 / 268) and a field to `LocalVar` or `Stmt`. Per-case code is growing faster than structure, and it compounds F2, F3 and F5.
- Fix direction: gate parity work on the F2/F3 seams (one type representation, sema pass). Then split by phase, not by size: `emitter_expr_call` → call / method / builtin-intrinsics / sizeof; `ast_helpers` → parser actions / enum registry / attrs.
- Ticket: #1818 (existing)

### N3. Type facts held as per-case flags on `LocalVar`/`Stmt` [cleanup → architecture] — Major
- Evidence: `LocalVar` grew from 11 to 39 fields. `add_local_full` writes all 39 by hand (`emitter_core.ritz:1372-1424`), including `inner_pointee_type`, `pointee_array_elem_pointee`, `ref_root_*`, `is_lent*`, `array_view`. `Stmt` grew from 31 to 49 fields, `EmitterState` from 46 to 82, and `Parser` `last_*` from 15 to 20.
- Impact: each new type shape needs a new field, plus a reset, plus a copy everywhere. Example: the `**T` inner pointee was added to 4 structs in `3950f7c2`.
- Fix direction: this is the F2 TypeRef, with a recursive pointee/element/shape. The 39 fields collapse to name + `*TypeRef` + binding-mode flags.
- Ticket: #1889 (existing)

### N4. Multi-field tuple variants don't parse in ritz1 [parity / language-gap] — Major
- Evidence: `enum Shape / Circle(i64) / Rect(i64, i64)` gives ritz1 `error: en.ritz:3:13: unexpected ','`, while ritz0 compiles it. The grammar allows only `IDENT LPAREN type_spec RPAREN` (`grammars/ritz1.grammar:314`). The spec shows `Rect(f64, f64)` (`LANGUAGE_SPEC.md:3319`, `:3486`).
- Fix direction: a `type_list` in `enum_variant` and an N-field payload layout, built on the struct-variant path (`:312`).
- Ticket: #1295 (existing)

### N5. No diagnostic module: ~60 bespoke error printers [cleanup] — Major
- Evidence: 42 hand-rolled `eprints_cstr(c"error: ")` sequences, up from 3. 18 of them are in `ast_helpers.ritz`, each with its own `if g_parse_file != null … "<input>"` fallback. Dup clusters: 15×, 13×, 12×, 11× and 10× (metrics). Error helpers include `let_error*`, `ref_error_*` (11), `own_error_*` (11), `gi_error*`, `si_error_at`, `enum_error_at` and `emit_ir_error*`. 56 `emit_ir_error` calls are still unlocated.
- Fix direction: one `diag_error(span, fmt…)` in a `diag` module, using `format_into` (#1824) and `SrcSpan` (`ast.ritz`), and a lint that no file outside `diag` calls `eprints_cstr(c"error: ")`.
- Ticket: #3445

### N6. Second and third IR-text rewrite passes [cleanup] — Major
- Evidence: `align_packed_accesses` (`emitter.ritz:637-657`) and `own_end_fn` (`ownership.ritz:3490-3525`) each copy the function body out of `s.out`, re-scan it line by line with `ll_line_len`/`ll_starts_with`, and re-emit it. Both are new since v4 and are counted in the F4 row.
- Fix direction: emit `align 1` at the GEP/load site from the struct's packed flag, and emit drops at `ret` emission (`emit_return`). Both need the typed IR builder (#1817).
- Ticket: #1817 (existing)

### N7. New silent capacity in the lexer bracket stack [cleanup] — Minor
- Evidence: introduced by `6f245b93` (the commit under review). At `lexer_nfa.ritz:953-955` bracket depth goes past 64, and `bracket_kinds` is then just not written. `:248` then skips the read. This is the #1813 pattern of degrading silently instead of failing loudly. `indent_stack` beside it does fail loudly (`:600`).
- Fix direction: give it a located error at depth 64, as `MAX_INDENT_DEPTH` has, or make it growable.
- Ticket: #3447

### N8. Leftover binary and makefile tracked [cleanup] — Minor
- Evidence: `projects/ritz/ritz1/ritz1_new` is a 107 KB static ELF, tracked since `2d283049` (Feb), and `ritz1/Makefile.working` is tracked too. Nothing references either (grep over py/sh/Makefile/toml). Review/4 missed both.
- Fix direction: `git rm`. Add a CI check that no ELF is tracked.
- Ticket: #3447

## Not findings

- `ritz1/src/sha256.ritz`: ritzlib has no SHA-256 and the compiler can't import cryptosec. The file header justifies it (`:1-7`).
- The `*.ritz.sig` files in `ritz1/src` are untracked local leftovers dated 2026-10-25 and are git-ignored (`projects/ritz/.gitignore:17`).
- `parser_gen.ritz` growth (6,357 → 8,137 SLOC): generated, and `regen-check` gates it (`Makefile:248-256`).
- The `char_code_compare` smell reads 0 again, but the tool misses `*(p + i) == 95` (e.g. `emitter_expr_call.ritz:4262`). The ~326 count above comes from a grep.
- About 16 functions are referenced only at their own definition (e.g. `lexer_debug_nfa`, `put_bytes`, `get_fn_count`). Some are used by tests. Not triaged.
