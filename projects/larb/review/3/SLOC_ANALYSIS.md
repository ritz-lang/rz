# LARB SLOC & Complexity Analysis

**Date:** 2026-02-17
**Tool:** `projects/larb/tools/ritz-stats/ritz_stats.py`
**Scope:** All `.ritz` source files under `projects/` (excluding `build/`, `target/` dirs)

---

## Ecosystem Metrics

### Overall (207,458 SLOC across 1,141 files)

| Metric | Value |
|--------|-------|
| Total lines | 317,750 |
| Source lines (SLOC) | 207,458 (65.3%) |
| Comment lines | 54,020 (17.0%) |
| Blank lines | 56,272 (17.7%) |
| Functions | 9,438 |
| Structs | 825 |
| Enums | 12 |
| Files | 1,141 |
| Avg function length | 10.5 lines |
| Avg cyclomatic complexity | 3.03 |
| Max cyclomatic complexity | 137 |
| Deepest nesting | 19 levels |

> **Note:** Raw counts include vendored copies inside `spire/httplib/ritz/` and `spire/httplib/ritzunit/`. See the Duplication section for details on effective unique SLOC.

### Per-Project Breakdown

| Project | SLOC | Files | Avg Lines/File | Largest File (lines) |
|---------|-----:|------:|---------------:|----------------------|
| ritz | 60,780 | 421 | 213.8 | `ritz1/src/parser_gen.ritz` (3,333) |
| spire | 35,879 | 193 | 292.6 | `httplib/test/test_hpack.ritz` (1,340) |
| cryptosec | 17,865 | 61 | 450.2 | `test/test_ed25519.ritz` (2,247) |
| harland | 12,419 | 53 | 380.7 | `kernel/src/main.ritz` (4,622) |
| mausoleum | 11,702 | 37 | 468.8 | `test/test_btree.ritz` (1,217) |
| http | 11,312 | 45 | 367.9 | `test/test_hpack.ritz` (1,340) |
| ritzlib | 10,499 | 59 | 292.0 | `sys.ritz` (863) |
| squeeze | 6,976 | 30 | 379.2 | `lib/deflate.ritz` (886) |
| tome | 6,680 | 16 | 648.2 | `lib/tome.ritz` (3,496) |
| zeus | 6,571 | 33 | 323.0 | `lib/zeus_client.ritz` (717) |
| valet | 6,429 | 21 | 502.4 | `lib/valet.ritz` (1,330) |
| lexis | 5,755 | 28 | 290.5 | `lib/html/tokenizer.ritz` (1,060) |
| prism | 5,352 | 43 | 185.3 | `test/simple_test.ritz` (460) |
| angelo | 4,197 | 27 | 233.4 | `src/tests.ritz` (786) |
| sage | 2,916 | 7 | 563.6 | `test/test_parser.ritz` (1,186) |
| ritzunit | 2,465 | 18 | 219.9 | `src/runner.ritz` (670) |
| iris | 2,177 | 17 | 194.2 | `lib/paint/mod.ritz` (394) |
| spectree | 1,705 | 10 | 273.8 | `test/test_mcp.ritz` (532) |
| goliath | 1,445 | 13 | 176.8 | `src/virtio_store.ritz` (392) |
| nexus | 1,316 | 19 | 109.4 | `src/presenters/page_presenter.ritz` (354) |
| tempest | 1,209 | 15 | 158.7 | `lib/chrome.ritz` (311) |
| indium | 477 | 17 | 49.3 | `user/init.ritz` (196) |
| ritz-lsp | 470 | 6 | 125.5 | `src/server.ritz` (236) |
| rzsh | 371 | 3 | 193.0 | `src/main.ritz` (247) |
| larb | 290 | 2 | 190.5 | `tools/ritz-stats/ritz_stats.ritz` (340) |

**Projects with the highest avg file size** (risk of large-file sprawl):
- `tome`: 648.2 avg lines/file
- `sage`: 563.6 avg lines/file
- `valet`: 502.4 avg lines/file
- `cryptosec`: 450.2 avg lines/file
- `mausoleum`: 468.8 avg lines/file

---

## Complexity Hotspots

### Deep Nesting (>4 levels)

182 functions exceed 4 levels of indentation. The worst offenders:

| Nesting | CC | Lines | Location | Function |
|--------:|---:|------:|----------|----------|
| 19 | 117 | 938 | `ritz/ritz1/src/emitter.ritz:714` | `emit_expr` |
| 12 | 27 | 90 | `cryptosec/lib/x509.ritz:511` | `x509_parse_extensions` |
| 10 | 2 | 15 | `valet/lib/tls/conn.ritz:447` | `tls_close` |
| 9 | 7 | 53 | `valet/lib/tls/conn.ritz:293` | `tls_send_server_hello` |
| 9 | 2 | 21 | `valet/lib/tls/conn.ritz:347` | `tls_send_encrypted_extensions` |
| 9 | 4 | 30 | `valet/lib/tls/conn.ritz:383` | `tls_send_finished` |
| 9 | 1 | 14 | `valet/lib/tls/keyschedule.ritz:310` | `keyschedule_derive_handshake_keys` |
| 9 | 1 | 16 | `valet/lib/tls/keyschedule.ritz:370` | `keyschedule_derive_app_keys` |
| 8 | 14 | 34 | `angelo/src/font.ritz:75` | `glyph_outline_with_depth` |
| 8 | 20 | 93 | `ritz/ritz1/src/emitter.ritz:620` | `emit_member_ptr` |
| 8 | 33 | 382 | `ritz/ritz1/src/emitter.ritz:2135` | `emit_stmt` |
| 8 | 55 | 130 | `ritz/ritzlib/meta.ritz:133` | `meta_free` |
| 8 | 24 | 140 | `squeeze/lib/deflate_simd.ritz:486` | `deflate_simd_compressed` |

The `emit_expr` function in the Ritz compiler is the single worst case: 938 lines, 19 levels of nesting, and CC 117. This is a massive monolith that handles every expression type through deeply nested conditionals.

The `valet/lib/tls/` cluster shows 9-level nesting in several short functions — likely caused by nested builder/callback patterns or sequential optional-unwrap chains that could benefit from early returns or helper extraction.

### Long Functions (>50 lines)

411 functions exceed 50 lines across the ecosystem. Per project:

| Project | Long Fns (>50 ln) | High CC (>=10) |
|---------|------------------:|---------------:|
| ritz | 176 | 183 |
| cryptosec | 60 | 21 |
| squeeze | 32 | 9 |
| mausoleum | 28 | 15 |
| harland | 24 | 11 |
| zeus | 12 | 1 |
| sage | 11 | 16 |
| lexis | 9 | 6 |
| valet | 8 | 6 |
| tome | 7 | 7 |
| angelo | 6 | 12 |
| ritzunit | 6 | 7 |

Top 20 longest functions (excluding vendored/archive duplicates):

| Lines | CC | Nesting | Location | Function |
|------:|---:|--------:|----------|----------|
| 938 | 117 | 19 | `ritz/ritz1/src/emitter.ritz:714` | `emit_expr` |
| 387 | 114 | 3 | `ritz/ritz1/src/parser_stmt.ritz:567` | `parse_assign_stmt` |
| 382 | 33 | 8 | `ritz/ritz1/src/emitter.ritz:2135` | `emit_stmt` |
| 381 | 112 | 3 | `ritz/ritz1/src/parser_gen.ritz:1529` | `parse_assign_stmt` |
| 315 | 44 | 7 | `ritz/examples/tier5_async/49_ritzgen/src/codegen.ritz:318` | `emit_rule_parser_ast` |
| 291 | 43 | 4 | `ritz/ritz1/src/emit_min.ritz:246` | `emit_expr` |
| 267 | 52 | 3 | `ritz/ritz1/src/parser_type.ritz:11` | `parse_type_spec` |
| 247 | 5 | 2 | `cryptosec/lib/sha256.ritz:242` | `sha256_transform_ni` |
| 235 | 36 | 7 | `ritz/examples/tier5_async/49_ritzgen/src/codegen.ritz:634` | `emit_rule_parser` |
| 224 | 46 | 3 | `ritz/ritz1/src/parser_gen.ritz:671` | `parse_type_spec` |
| 216 | 23 | 4 | `ritz/ritz1/src/emit_min.ritz:538` | `emit_stmt` |
| 209 | 39 | 4 | `ritz/examples/tier5_async/49_ritzgen/src/main.ritz:105` | `main` |
| 199 | 21 | 7 | `ritz/ritz1/src/emitter.ritz:1891` | `emit_assign` |
| 197 | 137 | 5 | `angelo/src/hinting/interpreter.ritz:139` | `execute_instruction` |
| 187 | 32 | 7 | `ritz/examples/76_tier3_http/src/main.ritz:164` | `run_server` |
| 185 | 16 | 3 | `harland/kernel/src/main.ritz:2381` | `sys_spawn_args_impl` |
| 172 | 70 | 5 | `sage/src/lexer.ritz:315` | `lexer_next` |
| 167 | 81 | 2 | `cryptosec/lib/sha512.ritz:121` | `get_k512` |
| 162 | 22 | 7 | `ritz/ritz1/src/emitter.ritz:1728` | `emit_var_decl` |
| 161 | 13 | 3 | `harland/kernel/src/main.ritz:3830` | `test_capability_system` |

### Long If-Else Chains / Large Match Blocks

The `elif`-chain pattern was not prevalent (the scanner found no `if/elif` chains exceeding 8 branches). However, large `match` blocks are common — several should be replaced with lookup tables or data-driven dispatch:

| Match Arms | Location | Function | Notes |
|-----------:|----------|----------|-------|
| 114 | `lexis/lib/dom/tag.ritz:526` | tag dispatch | HTML tag name -> enum mapping; ideal for a static array |
| 84 | `lexis/lib/dom/tag.ritz:240` | tag dispatch | Second large block in same file |
| 50 | `prism/src/input/keyboard.ritz:104` | `key_to_index` | Key code -> index mapping; use a lookup array |
| 36 | `angelo/src/hinting/interpreter.ritz:185` | instruction dispatch | TrueType bytecode opcodes; use a function pointer table |
| 22 | `angelo/src/hinting/instructions.ritz:163` | instruction names | Name -> enum; use a static table |
| 16 | `tempest/lib/document.ritz:245` | document node types | Could be a type->handler table |
| 15 | `lexis/lib/html/tree_builder.ritz:206` | insertion mode dispatch | Could be a table of handler functions |
| 14 | `nexus/src/errors/nexus_error.ritz:42` | error formatting | Could be a static message table |

**Separate concern — `get_k` / `get_k512` in cryptosec:**
These functions (`CC 65` and `CC 81`) are SHA round constant tables implemented as 64/80-way `if i == N return CONSTANT` chains. The high CC score is an artifact of the metric counting each branch; the actual algorithmic complexity is trivial. They should be replaced with static array constants, which is also likely to improve performance.

### Repetitive Code / Boilerplate

#### Exact File Duplication

97 groups of identical files were found, resulting in **18,410 redundant SLOC** across the ecosystem. The major duplication clusters are:

**1. `http` project mirrored verbatim inside `spire/httplib/`**

45 files are byte-for-byte identical between `projects/http/` and `projects/spire/httplib/`. This accounts for **11,312 redundant SLOC** — the single largest duplication in the ecosystem. The `spire` project appears to have a vendored snapshot of the entire `http` library rather than referencing it as a dependency.

Affected lib files (sample): `hpack.ritz`, `async_http.ritz`, `chunked.ritz`, `h1_request.ritz`, `h2_frame.ritz`, `quic_packet.ritz`, `qpack.ritz`, ... (22 lib files)

Affected test files (sample): `test_hpack.ritz`, `test_h2_frame.ritz`, `test_quic_packet.ritz`, ... (23 test files)

**2. `ritz` stdlib mirrored inside `spire/httplib/ritz/` and `spire/httplib/ritzunit/`**

The vendored Ritz compiler/stdlib appears twice inside `spire/httplib/` — once under `ritz/` and once under `ritzunit/`. Files like `ritzlib/meta.ritz`, `ritzlib/sys.ritz`, `ritzlib/async/executor.ritz`, etc. are duplicated (~40 pairs of identical files).

**3. Top-level loose files duplicated in `goliath/src/`**

Six shared module files exist both at the `projects/` root and inside `goliath/src/`:
- `projects/blob_id.ritz` == `projects/goliath/src/blob_id.ritz`
- `projects/blob_store.ritz` == `projects/goliath/src/blob_store.ritz`
- `projects/dir_entry.ritz` == `projects/goliath/src/dir_entry.ritz`
- `projects/error.ritz` == `projects/goliath/src/error.ritz`
- `projects/namespace.ritz` == `projects/goliath/src/namespace.ritz`
- `projects/path.ritz` == `projects/goliath/src/path.ritz`

**4. Example code duplicated between flat and tiered directory layouts**

- `ritz/examples/34_kill/src/main.ritz` == `ritz/examples/tier4_applications/34_kill/src/main.ritz` (338 lines each)
- `ritz/examples/74_async_tiers/tier2_echo_uring.ritz` == `ritz/examples/75_tier2_uring/src/main.ritz` (same content)

**5. Test helper duplication**

- `ritz/tmpknzolpt8/helpers.ritz` == `zeus/test/helpers.ritz`

#### Structural Boilerplate Patterns

The following repeated patterns appear across multiple projects and indicate missing abstractions:

- **`parse_assign_stmt` appears in both `parser_stmt.ritz` and `parser_gen.ritz`** with nearly identical logic (387 vs 381 lines, CC 114 vs CC 112). These are likely hand-written vs generated versions that have drifted in sync.

- **`emit_expr` appears in both `emitter.ritz` and `emit_min.ritz`** (938 vs 291 lines). `emit_min` is presumably a stripped-down variant; the shared sub-logic should be extracted into shared helpers.

- **The same `lexer_next` pattern** repeats in `sage/src/lexer.ritz` (CC 70, 172 ln), `ritz/examples/tier5_async/49_ritzgen/src/lexer.ritz` (CC 36, 181 ln), and the ritzlib lang lexer. Each was written independently rather than sharing a lexer combinator or table-driven tokenizer.

- **`hpack_decode_header_field`** is 149 lines, CC 22, and is duplicated identically in `http/lib/hpack.ritz` and `spire/httplib/lib/hpack.ritz`.

- **TLS handshake scaffolding** in `valet/lib/tls/conn.ritz` shows 9-level nesting in short send-functions (`tls_send_server_hello`, `tls_send_encrypted_extensions`, `tls_send_finished`, `tls_close`), suggesting a repetitive nested-builder pattern that could be collapsed.

---

### Files Needing Refactoring

Files > 500 lines (excluding vendored/archive copies): **110 files**. Critical cases:

#### Severely Oversized (>2,000 lines)

| Lines | Code | File | Issues |
|------:|-----:|------|--------|
| 4,622 | 2,915 | `harland/kernel/src/main.ritz` | 77 functions in one file; kernel monolith covering mm, fs, net, ipc, syscalls, tests, drivers |
| 3,496 | 2,417 | `tome/lib/tome.ritz` | 70 functions; document store, eviction, hashing, serialization all in one file |
| 3,333 | 2,567 | `ritz/ritz1/src/parser_gen.ritz` | Generated parser; 70 functions including 381-line `parse_assign_stmt` CC 112 |
| 3,198 | 2,646 | `ritz/ritz1/src/emitter.ritz` | 64 functions; `emit_expr` alone is 938 lines CC 117 nest 19 |
| 2,247 | 1,721 | `cryptosec/test/test_ed25519.ritz` | 57 test functions; test vectors could be data files |

#### Significantly Oversized (1,000–2,000 lines)

| Lines | Code | File | Issues |
|------:|-----:|------|--------|
| 1,964 | 1,138 | `tome/test/test_store.ritz` | 70 test functions; test file exceeds the library it tests |
| 1,701 | 1,044 | `cryptosec/lib/p256.ritz` | 13 functions; field arithmetic has very long hand-unrolled routines |
| 1,563 | 1,115 | `harland/boot/src/main.ritz` | 36 functions; bootloader monolith |
| 1,330 | 861 | `valet/lib/valet.ritz` | 53 functions; 0 detected by parser (all `pub fn` at file scope — parser limitation) |
| 1,319 | 923 | `ritz/ritz1/src/parser.ritz` | 32 functions; recursive descent parser |
| 1,244 | 923 | `ritz/ritz1/src/parser_expr.ritz` | 29 functions |
| 1,172 | 870 | `ritz/ritz1/src/ast_helpers.ritz` | 0 functions detected (all single-expression helpers below parser threshold) |
| 1,082 | 764 | `sage/src/parser.ritz` | 39 functions; avg 19 lines/fn but total still very large |
| 1,060 | 815 | `lexis/lib/html/tokenizer.ritz` | 26 functions; HTML spec tokenizer |
| 1,055 | 689 | `mausoleum/lib/btree.ritz` | 25 functions; `btree_insert_recursive` is 116 ln CC 18 |

#### Files with Structural Issues

- **`valet/lib/tls.ritz`** (1,144 lines, 0 functions detected): Either uses a syntax variant the parser doesn't detect, or is a large struct-definition + extern block file.
- **`valet/lib/static.ritz`** (968 lines, 0 functions): Same issue.
- **`ritz/ritzlib/sys.ritz`** (863 lines, 0 functions): Platform syscall definitions — likely all `extern fn` declarations. Fine structurally, but very large.
- **`ritz/ritz1/src/ast_helpers.ritz`** (1,172 lines, 0 functions): All helper constructors at module scope without `fn` keyword, or uses a pattern the analyzer misses.

---

## Recommendations

Prioritized by impact:

### P0 — Critical: Eliminate Duplication (saves ~18,410 SLOC)

**1. Convert `spire/httplib` vendored copy to a proper dependency reference.**
`spire/httplib/` contains a complete copy of `http/` (45 files, 11,312 SLOC). This is the largest single source of waste. Replace with a project dependency (`ritz.toml` `[dependencies]` entry pointing to `../http`). Any divergence between the copies will cause silent bugs over time.

**2. Remove the double-vendored Ritz stdlib in `spire/httplib/ritz/` and `spire/httplib/ritzunit/`.**
These are two more complete copies of the Ritz stdlib/compiler inside `spire`. Consolidate to a single reference.

**3. Canonicalize the `goliath` shared modules.**
`blob_id.ritz`, `blob_store.ritz`, `dir_entry.ritz`, `error.ritz`, `namespace.ritz`, `path.ritz` exist both at `projects/` root and inside `goliath/src/`. Pick one location and import from there.

### P1 — High: Break Apart Monolith Files

**4. Split `harland/kernel/src/main.ritz` (4,622 lines).**
This file contains the entire Harland kernel: memory management, filesystem, networking, IPC, syscall handlers, driver bindings, and tests. It should be split into at minimum: `syscall.ritz`, `mm/scheduler.ritz`, `fs/vfs_dispatch.ritz`, `net/stack.ritz`, and `test/kernel_tests.ritz`. The existing `harland/kernel/src/mm/`, `harland/kernel/src/fs/`, `harland/kernel/src/net/` directories exist — the logic from `main.ritz` should migrate there.

**5. Split `tome/lib/tome.ritz` (3,496 lines, 70 functions).**
The store engine, eviction policy, hash functions, and document serialization are all in one file. Suggested split: `store.ritz`, `eviction.ritz`, `serialization.ritz`, `index.ritz`.

**6. Split `ritz/ritz1/src/emitter.ritz` (3,198 lines).**
`emit_expr` at 938 lines with CC 117 and 19 levels of nesting is the single most complex function in the entire ecosystem. It handles every expression node type inline. Decompose into per-category helpers: `emit_expr_binary`, `emit_expr_call`, `emit_expr_match`, `emit_expr_unary`, etc. Similarly, `emit_stmt` (382 lines, CC 33) and `emit_assign` (199 lines, CC 21) should be extracted into focused helpers.

### P2 — Medium: Replace Lookup Tables

**7. Replace `cryptosec/lib/sha256.ritz::get_k` and `sha512.ritz::get_k512` with static arrays.**
These are SHA round constant tables (64 and 80 entries) implemented as `if i == N return CONSTANT` chains. CC scores of 65 and 81 are misleading — the logic is trivial — but the implementation is slower than a static array lookup and produces unnecessary machine code bloat. Replace with `let K: [u32; 64] = [0x428a2f98, ...]`.

**8. Replace `lexis/lib/dom/tag.ritz` large match blocks with a static table.**
Two match blocks with 114 and 84 arms map HTML tag name strings to enum variants. A sorted static `(str, TagKind)` array with binary search, or a compile-time hash map, would be cleaner and faster.

**9. Replace `prism/src/input/keyboard.ritz::key_to_index` with a lookup array.**
50-arm match mapping key codes to indices (CC 51). A direct index array `KEY_TABLE[keycode]` with bounds check eliminates this entirely.

**10. Replace `angelo/src/hinting/interpreter.ritz::execute_instruction` opcode dispatch.**
CC 137, 197 lines, 36-arm match. TrueType bytecode interpreters are canonical use cases for function pointer tables indexed by opcode byte.

### P3 — Normal: Reduce Long Parser/Emitter Functions

**11. `parse_assign_stmt` duplication in `parser_stmt.ritz` and `parser_gen.ritz`.**
Both contain a ~385-line version of the same function (CC 114/112). If `parser_gen` is truly a generated file, ensure the generator produces smaller, more modular output. If it is hand-written, consolidate.

**12. `sage/src/lexer.ritz::lexer_next` (CC 70, 172 lines) and `sage::check_keyword` (CC 54, 121 lines).**
The `sage` project implements a full lexer in two monolithic functions. `lexer_next` should be broken into character-class dispatchers, and `check_keyword` should use a sorted keyword table with binary search rather than a sequential match.

**13. `ritz/ritzlib/meta.ritz::meta_free` (CC 55, 130 lines, 8 levels nesting).**
This is the generic memory management function and is unusually complex. Deep nesting to level 8 in a 130-line function suggests this could be decomposed into type-specific free helpers called from a smaller dispatch function.

**14. `squeeze/lib/deflate.ritz` compression functions.**
`deflate_compressed` (CC 20), `limit_code_lengths` (CC 26), `rle_encode_lengths` (CC 14, nest 7), `build_code_lengths` (CC 16). The DEFLATE codec has 32 long functions in 886 lines. The nesting in `rle_encode_lengths` to level 7 suggests loop-within-loop-within-conditional structure that could use early continue/return patterns.

### P4 — Low: Parser Tool Gaps

**15. The `ritz_stats.py` function detector misses `pub fn` at file scope when no indented body follows before the next `pub fn`.**
This causes `valet/lib/valet.ritz` (53 functions), `valet/lib/tls.ritz`, `valet/lib/static.ritz`, and `ritz/ritz1/src/ast_helpers.ritz` to report 0 functions. The `ritz_stats.ritz` Ritz implementation should handle this correctly when it ships.

---

## Summary

| Category | Count | SLOC Impact |
|----------|------:|------------:|
| Exact duplicate files | 97 groups | 18,410 redundant SLOC |
| http↔spire duplication alone | 45 files | 11,312 redundant SLOC |
| Functions > 50 lines | 411 | ~15,000 affected SLOC |
| Functions with CC >= 10 | 330 | high maintenance risk |
| Files > 500 lines | 110 | ~180,000 total lines in oversized files |
| Files > 1,000 lines | 40 | ~75,000 total lines in critically large files |

The two most actionable wins are: **(1)** resolving the `http`/`spire` duplication (11K SLOC, zero risk) and **(2)** beginning the decomposition of `harland/kernel/src/main.ritz` and `ritz/ritz1/src/emitter.ritz` into module-organized files, which will dramatically improve navigability and testability of the two most central codebases in the ecosystem.
