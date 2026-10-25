# LARB v4 Review: ritz1 (self-hosted compiler)

**Reviewed:** 2026-10-25 · **Metrics:** [metrics-ritz1.md](metrics-ritz1.md) · **Status:** CRITICAL
**Method:** `INSTRUCTIONS_v4.md`, read-only (no builds were permitted). Scope:
`projects/ritz/ritz1/src` (23 files, 34,760 lines, 25,641 SLOC, 758 functions),
plus the generator and grammar. Each finding was checked against the code by
the reviewer before it was written down. Claims that need a build to confirm are marked
**(unconfirmed)**, and their tickets start with a red test.

## Summary

ritz1 self-hosts, but its shape is that of a C program written in Ritz syntax:
- 0 `enum`s, 0 `match`es, 0 `impl` blocks, 1 `bool` in the front end;
- names as 239 `(*u8, len)` pairs;
- IR assembled from 3,698 C-string fragments;
- fixed-capacity global tables that **silently drop data** when full.

Architecturally there is **no semantic phase**. Types are inferred while IR is
being written, by four separate inference engines that talk through
side-channel fields. Eleven separate type→LLVM/size tables have
already drifted apart into a layout bug. The emitter is one module split into 10 files
by size, with a 7-module import cycle. Most of this is **cleanup**: the
language already has the tools. Two items are genuine **language gaps**:
formatting into a buffer, and inline `asm`, which is specified nowhere even
though ritz0 implements it. One is a parity gap: ritz1 payload enums.

## Findings

### F1. Silent data loss at fixed capacities and unhandled kinds [cleanup] — Critical → #1813
- `MAX_ENUMS = 32` (`ast_helpers.ritz:3009`): `enum_def_start` returns 0 for
  the 33rd enum (`:3045-3047`), and `enum_variant_record` then appends its
  variants to `g_enum_count - 1` (`:3058-3075`), which is **the 32nd enum**.
- `arg_regs: [16]i32` + `if arg_count < 16` (`emitter_expr_call.ritz:333`,
  `:1641`, `:1708-1715`, `:3186`): argument 17 and beyond is not emitted at all.
- `add_local_full` ignores local number 257 (`emitter_core.ritz:546`).
  `add_instantiation` returns -1, which all 3 callers ignore (`monomorph.ritz:64`,
  `:295/:743/:1418`). That is the table whose saturation caused #1325.
- `ptr.field[i] = v` parses (`parser_gen.ritz:4892` → `STMT_MEMBER_INDEX_ASSIGN`,
  `ast_helpers.ritz:1767`), but no emitter arm handles it. `emit_stmt`'s
  default arm writes `; TODO: statement kind N` (`emitter_stmt.ritz:2948-2951`)
  and the compile succeeds **(unconfirmed)**.
- A tab in indentation: `lexer_handle_indent` returns `TOK_ERROR` without
  advancing (`lexer_nfa.ritz:332-334`), and `tokenize` loops on it
  (`main.ritz:120-145`), so it probably never terminates **(unconfirmed)**.
  `indent_stack[64]` has no bound, and `MAX_INDENT_DEPTH` is unused (`:33`, `:361`).
- `find_fn/find_struct/find_global` treat an fnv1a collision as "not found"
  (`emitter_core.ritz:580-625`).

### F2. Eleven type tables that disagree [cleanup] — Critical → #1814
- A `[N]u16` struct field is declared `[N x i64]`: the array-element ladder in
  `emit_field_llvm_type` has no u16/i16/u32 arm (`emitter_core.ritz:2620-2638`).
- The same field is sized 2N by `get_struct_size_by_name` (`:2000-2062`).
- `bool` and `f32` fields are sized at 8, and alignment is "simplified to 8" (`:2036`, `:2041`).
- The eleven tables are listed in #1814.
- A type is an `i32` code plus loose name, pointee and array fields, repeated on 8 structs, and the
  `Parser` carries 14 `last_*` side channels because `type_spec` returns an `i32`
  (`ast.ritz:500-537`).

### F3. No semantic phase [architecture] — Critical → #1816
- **The pipeline has no checking stage.** It is parse → monomorph → emit (`main.ritz:756-781`).
- **Type inference happens during emission.** `get_expr_type` (`emitter_core.ritz:2363`, CC 53, ~40 callers) falls back to `TYPE_I64`.
  `emit_var_decl` (CC 217) is mostly inference, and it writes back into the AST 55
  times. It also emits the initializer early so it can learn its type.
- **Two more inference engines exist.** One is in monomorph (`g_lv_*`); the other is narrowing, which runs from the emitter.
- **Side-channel fields carry types between functions.** These are `last_match_agg_name`, `ctx_enum_*`, `ctx_simd_*`, `sret_last_*` and `last_expr_*`.
- **Calls are never checked.** User calls get no arity or type check (#1629).
- **Diagnostics carry no source location.** `emit_ir_error`, at `:215`, prints none.

### F4. IR built by string concatenation [cleanup + language-gap] — Major → #1817, #1824
- **Every instruction is spelled out by hand.** It is `next_reg` + `emit_str(s, c"  ")` + `emit_reg` + text.
  That adds up to 560 / 559 / 1,353 calls and 3,585 literals.
- **The same ladders are copy-pasted.** The trunc ladder appears 19 times, and the ext ladders appear 13, 10 and 6 times.
  Argument narrowing and return widening are each copied 3 times.
- **Two passes re-parse the IR text the emitter just wrote.** They are
  `hoist_entry_allocas` and `rewrite_large_struct_copies` + `ll_copy_scan.ritz`.
- **The language-gap part:** `{expr}` interpolation exists only for `print`/`eprint`
  (`LANGUAGE_SPEC.md:226`), so nothing can format into a `String` (#1824).

### F5. Decomposition and layering [architecture] — Major → #1818
Twelve functions exceed 300 SLOC, led by `emit_expr_index` (885, CC 299) and `emit_expr_call`
(854, CC 278, depth 18). That nesting depth is a 16-level hand-unrolled character
compare for `"__builtin_alloca"`, at `emitter_expr_call.ritz:1466-1485`.

Structural problems:
- The import graph has one strongly connected component of 7 emitter modules.
- `emitter_print` imports `interp`, which imports `parser_gen` and `lexer_nfa`: emission re-parses source text.
- `emitter_core` is a grab bag of 107 functions, and `EmitterState` has 46 fields, about 120 KB of inline arrays.

Proposed layering: base → syntax → sema → mono → codegen → driver.

### F6. Generated parser: correct but bloated; grammar encodes 14 assignment special cases [generator] — Major → #1819
**Checked:** `parser_gen.ritz` is pure generator output. Every commit that touches it
also changes the grammar, and `regen-check` gates it. A reviewer's claim of
"hand edits" was **wrong and is not filed**. Keep it checked in.

The grammar and generator problems:
- **`parse_assign_stmt` (683 SLOC):** 14 of its 16 alternatives are special-case lvalue shapes. The two generic ones already cover them.
- **Unused captures:** 69% of token captures are never used.
- **No FIRST-set dispatch,** so every call statement is parsed three times.
- **No rollback on backtracking:** parser actions run on failed alternatives without undoing their state.
- **Dead leftovers:** `generator.py`, `ritz.grammar`, and the `.old` grammars.
- **Wrong comment:** the Makefile's "ast_helpers diverged by design" refers to a generated sibling that doesn't exist.

### F7. C in Ritz clothing [cleanup] — Major → #1820
- **Names:** 239 `(*u8, len)` pairs, where `StrView` fields already compile under ritz1 (`main.ritz:558-565`).
- **Compare helpers:** five hand-rolled ones (`name_eq`, `buf_eq`, `starts_with`, `ll_starts_with`, `ll_text_eq_n`), where `strview_eq` exists.
- **ASCII codes:** about 130 numeric comparisons instead of character literals.
- **Booleans:** 389 `i32`-as-bool sites.
- **Kind codes:** `const i32` values with if-ladders where an enum and `match` belong.
- **Allocation sizes:** 28 hard-coded `parser_alloc` sizes. One struct is allocated as 80 bytes in one place and 64 in another.
- **Global state:** 40 module-level `var`s.
- **Debug output:** unconditional `[MONOMORPH]` lines on stderr.

### F8. The compiler works around its own miscompiles [language-gap: compiler bugs] — Major → #1815
- **Pointer arithmetic:** `(p + a) + b` gets no stride scaling on the second `+` (`nfa.ritz:228-234`).
- **Store width:** the `*i32` store width at `main.ritz:109`.
- **Compound dereference:** a compare and read-modify-write quirk, worked around three times in `ast_helpers.ritz:3067-3124`.
- **Field access:** `(*a.b).c` (`lexer_nfa.ritz:510`).
- **Possibly stale:** a PHI workaround (`fn_cache.ritz:658`).

Under No Concessions these are compiler bugs that every user hits.

### F9. Runtime NFA lexer [generator] — Minor → #1821
The lexer is rebuilt from regex strings for every file and every placeholder, using about 557 KB of stack, and it matches by recursive backtracking. Its tie-break rule contradicts the file header. The escape cooker is copied three times. `lexer_next` has CC 98 and nests 14 deep.

### F10. Cache fast path ignores imports [cleanup] — Critical (filed under fast iteration) → #1807
`check_source_unchanged` (`fn_cache.ritz:827-880`) never checks import hashes,
and the per-function cache has no callers.

### F11. Enums are not in the AST [architecture / parity] — Major → #1295 (existing)
`Module` has no enum list (`ast.ritz:403-409`). Variants live in global
parallel arrays, monomorph hard-codes the arity of `Result` and `Option`
(`monomorph.ritz:415-420`), and `enum_def_skip` discards enum definitions
(`ast_helpers.ritz:2985-2991`). Until ritz1 has payload enums (#1295), its own AST
can't become a tagged union. The mangling is string-based with `$` components
(`monomorph.ritz:966-970`). Spec §11.4 joins with `_`, and whether the emitted symbols
diverge needs a build to check.

### Stale documentation → #1827
`ARCHITECTURE.md` says 11 files and 13.7k lines; there are 23 files and 34.8k lines. Its import graph is wrong, and it cites NFA limits that have been removed. `SELF_HOSTING_PLAN.md` says for-loops are not implemented and refers to files that don't exist.

## Language gaps vs. cleanup

| Need | Status | Ticket |
|---|---|---|
| Format into `String` | Missing (print/eprint only) | #1824 |
| Inline `asm` | Implemented by ritz0, absent from the spec, missing in ritz1 | #1825 |
| Closures | Implemented by ritz0 (expression form); the spec says they "never existed" | #1623 (evidence appended) |
| Payload enums in ritz1 | Spec and ritz0 have them; ritz1 does not | #1295 |
| Generic `HashMap<K,V>` | `hashmap.ritz:13` says multi-param generic casts are unsupported. Probably stale after #1299 (nested generics); verify. | — (verify first) |
| `bool`, `StrView`, `enum`+`match`, `Vec<T>`, `sizeof`, char literals | Exist and compile under ritz1 | #1820 |

## Not findings

- `parser_gen.ritz` being checked in: correct, given `regen-check`.
- ritz1 refusing to write output when `error_count > 0` (`main.ritz:797`): correct. The defect is
  that errors carry no location and cascade (F3), not that junk IR reaches disk.

## Tickets

Epic **#1812**. Ordered: correctness → language → architecture → cleanup.

| Ticket | Pri | Finding |
|---|---|---|
| #1813 | 80 | F1: silent capacity drops, unhandled statement kind, tab hang, hash collisions |
| #1814 | 80 | F2: one TypeRef and one type table (`[N]u16` layout bug) |
| #1815 | 80 | F8: pointer-stride and other miscompiles worked around in ritz1's source |
| #1807 | 90 | F10: stale-IR cache (fast-iteration epic #1801) |
| #1824 | 70 | Language: format into a buffer |
| #1825 | 70 | Language: specify `asm`, port it to ritz1, move the syscall shims into ritzlib |
| #1823 | 65 | ritz0: type checker opt-in and never enabled |
| #1816 | 65 | F3: sema phase (after #1814) |
| #1817 | 65 | F4: typed IR builder (after #1814) |
| #1818 | 60 | F5: decomposition and layering (after #1816 and #1817) |
| #1822 | 60 | ritz0: 15k dead lines and a liveness guard |
| #1819 | 55 | F6: ritzgen v2 and grammar simplification (after #1813) |
| #1820 | 55 | F7: use the language's own features |
| #1821 | 50 | F9: generated scanner |
| #1826 | 45 | ritz0: emitter split (after #1822) |
| #1827 | 40 | Stale ritz1 docs |
