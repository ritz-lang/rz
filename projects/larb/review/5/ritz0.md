# LARB v5 Review: ritz0 (Python bootstrap compiler)

**Reviewed:** 2026-11-16 · **Baseline:** review/4 (2026-10-25) · **Status:** NEEDS WORK
**Metrics:** [metrics-ritz0.md](metrics-ritz0.md) (baseline [4/metrics-ritz0.md](../4/metrics-ritz0.md)) · **Measured on:** main @ 6f245b93
**Method:** `INSTRUCTIONS_v4.md`, read-only. Same path set as review/4: `ritz0/*.py` and `ritz0/emitter/*.py` minus `test_*.py` and `conftest.py`. Review/4's numbers reproduce exactly from `30815afa` with this selection (28 files, 26,415 SLOC, 971 fns). No AGAST lookups: ticket progress is taken from commit messages, and every status below was checked against code.

## Summary

The Critical from review/4 is gone. All ~11,900 dead `.py` lines, the `.orig`, the `.old` grammars and the ELF binary were deleted (`1596e716`), and a reachability guard now runs in `tools-unit`. Duplicate clusters fell from 884 to 126, and none now has 8 or more copies. `asm` is now specified (§18.6) and ritz1 lowers it. Everything else moved the wrong way. The live compiler grew by about 12,200 lines (+49%) in three weeks. `emitter_llvmlite.py` alone went from 12,432 to 17,385 lines, and 208 commits touched it. Functions nesting 6 or more levels deep went from 102 to 185. The type checker is still opt-in, so new language rules keep landing in the emitter and in four separate type inferers. The status is NEEDS WORK: nothing here is a correctness emergency, but the decomposition debt (F2) is growing faster than anything is paying it down, and it now exceeds every Critical threshold.

## Against review/4

| id | title | r4 sev | now | evidence | ticket |
|---|---|---|---|---|---|
| F1 | 41% dead code, tests testing the dead copy | Critical | **FIXED** | `parser_gen.py`, `parser_adapter.py`, `emitter/{calls,exprs,literals,patterns,stmts,struct_layout}.py`, `async_transform.py`, `ast_builder.py`, `parser_gen.py.orig`, `cat_ll` and `grammars/*.old` are all gone (`1596e716`). `emitter/test_struct_layout.py:15` now imports the live `emitter_llvmlite.FieldLayout/StructLayout/StructRegistry`. Guard: `tools/check_liveness.py` (reachability, backups, ELF), run by `tools/test_check_liveness.py:169` under `make tools-unit`; `python3 tools/check_liveness.py` passes today. Residue: `symbol_table.py` (539 lines) is still allowlisted, see N5. | #1822 |
| F2 | Live emitter is one 12.4k-line class | Major | **REGRESSED** | Now 17,385 lines / 13,038 SLOC / 518 fns (was 12,432 / 8,727 / 256). `class LLVMEmitter` spans `:650`–`:17091`, about 16,400 lines. Instance fields set in `__init__` went from 69 to 102. Emitter fns over 150 SLOC: 7 → 10. CC > 30: 19 → 22. Depth ≥ 6: 47 → 105. Depth ≥ 9: 6 → 20. `_try_emit_simd_builtin :12463` is unchanged (477/145), and the aesenc ladder is still there (`:12878-12993`). `_emit_stmt_inner :6274` went from 358/119 to 425/151, depth 11. New: `_dispatch_method_call :13741` at 269/127, depth 13 (the deepest in ritz0). No commit cites #1826. The only extraction was 8 small `*_rules.py` message modules (516 lines). By the v4 thresholds this is now Critical on file size, function SLOC and CC. | #1826 |
| F3 | Type checker opt-in, nothing opts in | Major | **PARTLY** | `--check-types` and `--check-names` are still `store_true`, default False (`ritz0.py:118-119, 485-489, 285, 298`). Nothing in `build.py`, `test_runner.py`, `tools/`, `scripts/` or the `Makefile` passes them. What changed: the corpus crash and false-positive pass (`0011dcbe`, "both stay opt-in"), and a slots-only `TypeChecker` that now runs on every compile (`type_checker.py:2225-2232`, called from `emitter_llvmlite.py:17360`). That turns on the 24 `_slot_error`/`_report_once` call sites. The 44 `self._error(` sites are still computed and then discarded by `_error` (`type_checker.py:2215-2218`) on the default path. Default-on now also covers binder, reachability and ref-slot checks (`ritz0.py:270-282`). | #1823 |
| F4 | Spec says `asm` and closures don't exist | Major | **PARTLY** | `asm`: **fixed**. Spec §18.6 now has a grammar and positive compile-gated examples (`LANGUAGE_SPEC.md:5597-5632`, `6167ac0e`). The ritz0 parser takes the clauses (`parser.py:1931-1993`), and ritz1 lowers asm (`ritz1/src/emitter_asm.ritz`, `bb6af962`). Closures: **open**. §5.6 (`LANGUAGE_SPEC.md:1557-1560`) still says the `\|...\|` form "never existed in the compiler". ritz0 still parses it (`parser.py:1671`) and lowers it (`_emit_closure :10931`, 168 SLOC). Users remain (`test/features/test_closures*.ritz`, `ritz0/test/test_level39.ritz`), and `87b24ff2` (2026-11-15) worked on the path again. LARB R56 recommends REMOVE but is "awaiting Aaron" (`review/4/rulings-2026-11.md:1842`). | #1825, #1623 |
| F5 | Duplicate infrastructure across compilers | Minor | **PARTLY** | The cache-path collision is fixed: sigs are now namespaced per compiler, outside the tree (`emitter/fn_cache.py:276-308`, `8d2b27db`). Two cache implementations remain by decision. The mangling divergence review/4 couldn't verify is now **verified**. `fn first<A,B>(p: Pair<A,B>)` at `<i32,u8>` emits `first$i32_u8` / `Pair$i32_u8` from ritz0 (matching §11.4, `LANGUAGE_SPEC.md:3767+`) and `first$i32$u8` / `%Pair$i32$u8` from ritz1 (`ritz1/build/debug/ritz1`, repro `/tmp/r5mono/m.ritz`). The defect is ritz1's (`ritz1/src/monomorph.ritz:701,804,887` split on `$`). | #1807 (+ ritz1 #3446) |

## Metrics delta

| metric | review/4 | now |
|---|---|---|
| files / lines / SLOC / fns | 28 / 36,650 / 26,415 / 971 | 39 / 38,977 / 29,494 / 1,340 |
| dead (non-reachable) `.py` lines | ~11,880 | 539 (`symbol_table.py`) |
| live compiler lines (excl. dead and in-dir test harness¹) | ~24,770 | ~36,950 (+49%) |
| `emitter_llvmlite.py` lines / SLOC / fns | 12,432 / 8,727 / 256 | 17,385 / 13,038 / 518 |
| files > 1500 SLOC (> 3000) | 3 (1) | 5 (1): emitter 13,038, parser 2,286, monomorph 1,990, move_checker 1,802, type_checker 1,767 |
| fns > 150 SLOC (> 300) | 12 (3) | 13 (2) |
| fns CC > 30 (> 80) | 49 (8) | 49 (7) |
| fns depth ≥ 6 (≥ 9) | 102 (14) | 185 (38) |
| top SLOC | `_try_emit_simd_builtin` 477 | same, 477 |
| top CC | `_try_emit_simd_builtin` 145 | `_emit_stmt_inner` 151 |
| top depth | `_emit_enum_match` 12 | `_dispatch_method_call` 13 |
| dup clusters total / ≥ 3 / ≥ 8 | 884 / 121 / 18 | 126 / 18 / 0 |
| smells: bare_except / shell=True / `global` | 0 / 0 / 2 | 0 / 0 / 13 (7 in the test harness, 2 in `monomorph.py` save/restore) |
| emitter `raise EmitError` / `raise ValueError` | 13 / 184 | 134 / 152 |

¹ `batching.py`, `fast_link.py`, `ritz0_inproc.py`, `spawn_guard.py`: 1,484 lines, reached only through `conftest.py` (N3).
The path set leaves out `test_runner.py` (976 lines), as review/4's did, even though the liveness guard counts it as production.

## New findings

### N1. Four independent Ritz type inferers, and the emitter's is the biggest [architecture] — Major
- Evidence:
  - `emitter_llvmlite._infer_ritz_type :1616` is 182 SLOC / CC 111, up from 114/63. Next to it are `_infer_unsigned_expr :15142` (69/43) and `_infer_float_expr :15317` (33/18).
  - `type_checker._infer_type :438` is 149/65.
  - `move_checker._infer_expr_type :514` is 91/42.
  - `monomorph._infer_value_type :1244` is 80/46, with `_infer_method_call_type :1388`.
  - Each re-derives literal typing (the dup clusters `emitter:1628`/`move_checker:521` and `emitter:1641`/`type_checker:463`).
  - The emitter also runs the move checker itself (`:2629`) and reads its `MoveTypes` (`:1624`).
- Impact: every typing rule (R-rulings, the "ritz0 refuses X" commits) has to be added in up to four places, or it lands only in the emitter. That is why the emitter's `EmitError` raises went from 13 to 134. It is F3's root cause, and it now shows up as code volume.
- Fix direction: one typing pass that annotates the AST (a `Typed` side table keyed by node), run by default. The emitter, move checker and monomorph read it, and their private inferers are deleted. Acceptance: one `_infer*` per expression kind across ritz0 (grep), and `--check-types` removed as a flag.
- Ticket: #3448.

### N2. Threshold breaches outside the emitter [architecture] — Major
- Evidence:
  - `ritz0.compile_file :117` went from 142/36/depth 6 to 194/55/depth 9.
  - `move_checker._check_expr :1267` went from 95 SLOC/depth 8 to 220/106/depth 11. `_check_one_stmt :1022` is 108 SLOC at depth 11.
  - `batching.merge :167` is CC 60, depth 9.
  - Files newly over 1,500 SLOC: `monomorph.py` (1,483 → 2,554 lines), `move_checker.py` (642 → 2,264), `type_checker.py` (1,079 → 2,232).
- Fix direction: split `compile_file` into a pass list (parse → resolve → check[] → monomorph → emit), which also gives N1 a home. Split `move_checker._check_expr` per expression kind, as a dispatch table.
- Ticket: #3449.

### N3. The test harness lives in the compiler package and is hashed as compiler [architecture] — Minor
- Evidence:
  - `batching.py`, `fast_link.py`, `ritz0_inproc.py` and `spawn_guard.py` (1,484 lines) are imported only by `conftest.py:136-138`.
  - `ritz0/` also holds 465 `test_*.py` files (136k lines), 195 of them `test_ritz1_*.py`.
  - `hash_ritz0_sources` excludes only `test_*` prefixes and `test/` (`emitter/fn_cache.py:337-338`). So `conftest.py` and these four files are part of the ritz0 compiler hash, and editing the test harness invalidates every ritz0 sig and cached artifact.
- Fix direction: move the harness and the cross-compiler tests into a `tests/` package outside `ritz0/`. Hash the compiler's reachable import set (`check_liveness` already computes it), not a directory walk.
- Ticket: #3450.

### N4. 152 unlocated `ValueError`s in the emitter; one hides a compiler disagreement [cleanup] — Minor
- Evidence: `grep -c "raise ValueError" emitter_llvmlite.py` gives 152. Repro `/tmp/r5mono/b.ritz` (`impl Box<T>` without `<T>`, then `b.get()`): ritz0 prints "Compiler error: No method 'get' found for type 'Box$u32'" plus a 60-line traceback (`_dispatch_method_call :13939`), while ritz1 compiles it and exits 0.
- Fix direction: convert these to located `EmitError` (the pattern from `87b24ff2`), and decide whether a free `T` in `impl X<T>` is an error in both compilers. Acceptance: `raise ValueError` count in the emitter is 0.
- Ticket: #1390 (existing).

### N5. `symbol_table.py` is kept alive by a stale allowlist entry [cleanup] — Minor
- Evidence: `tools/check_liveness.py:41` exempts it as "the interface model for #1810". But #1810 landed as `module_interface.py` (`e98e5a2c`), which doesn't use it. `symbol_table.py` hasn't changed since `84786d47` (2026-04-22) and has no production importer.
- Fix direction: delete it and `test_symbol_table.py`, and drop the entry.
- Ticket: #3450.

### N6. Escape decoding written twice in the lexer [cleanup] — Minor
- Evidence: the same `\n \t \r \\ " '` ladder appears in `_lex_string` (`lexer.py:228-240`) and `_lex_cstring` (`:403-414`). This is the only non-emitter dup cluster with ≥ 4 copies. `_lex_string` itself is 140 SLOC / CC 44 (was 109/42).
- Fix direction: one `_decode_escape(ch) -> str` table used by both.
- Ticket: #3450.

## Not findings

- The `*_rules.py` modules (8 files, 516 lines) are small and mostly message constants. They are deliberate: ritz1 prints the same strings, and tests hold both compilers to them (`ref_rules.py:1-8`). This is good shared policy, not fragmentation.
- `monomorph.py:2467,2525` `global _TYPE_ALIASES` is a save/restore-scoped table. An alias-through-emitter repro (`/tmp/r5mono/a.ritz`, `Box<Id>` with `type Id = u32`) mangles to `Box$u32` correctly.
- `async_transform_v2.py` is still named `_v2`. v1 is gone, so it can now be renamed; that's cosmetic.
