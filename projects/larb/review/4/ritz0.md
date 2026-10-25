# LARB v4 Review: ritz0 (Python bootstrap compiler)

**Reviewed:** 2026-10-25 · **Metrics:** [metrics-ritz0.md](metrics-ritz0.md) · **Status:** NEEDS WORK
**Method:** `INSTRUCTIONS_v4.md`, read-only (no builds). Scope: `projects/ritz/ritz0/*.py` excluding tests.

## Summary

ritz0 is the reference compiler and the oracle for every differential gate, so
its quality bounds everyone's. It works, but **about 15,000 of its 36,700
non-test lines (41%) are never imported by production code**. These are two
abandoned rewrites (an `emitter/` mixin package and a generated parser plus
adapter), with tests that exercise the dead copies. The live emitter is one
12,432-line file. The type checker exists but is **opt-in** (`--check-types`)
and no build path turns it on. And the normative spec says two features ritz0
implements do not exist.

## Findings

### F1. 41% of ritz0 is dead code, and some of its tests test the dead copy [cleanup] — Critical

Production importers, via `grep -rlE '^(from|import) <mod>\b'` excluding tests:

| Module | Lines | Production importers | Notes |
|---|---|---|---|
| `emitter/calls.py`, `exprs.py`, `literals.py`, `patterns.py`, `stmts.py` | 5,336 | **none** | Mixin classes (`ExprEmitterMixin`, `StmtEmitterMixin`, …) from the "Phase 3 compiler rewrite" `b4f8c5c` (2026-04-22), never wired in. They duplicate live methods: `_try_emit_simd_builtin` (live `emitter_llvmlite.py:8692`, 477 SLOC; dead `emitter/calls.py:255`, 442 SLOC), `_emit_closure` (`:7589` vs `emitter/exprs.py:909`), `_emit_asm` (`:4958` vs `emitter/stmts.py:604`). |
| `emitter/struct_layout.py` | 155 | **none** | Live layout is `emitter_llvmlite.py:233-266` (`FieldLayout`, `StructLayout`, `StructRegistry`). **`emitter/test_struct_layout.py:15` imports the dead copy**, so its tests prove nothing about production layout, which is the area of #1659/#1674. |
| `parser_gen.py` + `parser_adapter.py` | 4,632 | only each other | Production parses with hand-written `parser.py` (`ritz0.py:26`). `parser_gen.py` is "AUTO-GENERATED … from grammars/ritz.grammar"; nothing regenerates or diffs it (`regen-check` covers only ritz1's outputs). |
| `parser_gen.py.orig` | 3,142 | — | Merge leftover in git. |
| `async_transform.py` | 680 | none | Superseded by `async_transform_v2.py` (imported by `emitter_llvmlite.py`). |
| `ast_builder.py` | 538 | none | |
| `symbol_table.py` | 539 | tests only | Interface model for separate compilation: keep it and wire it in (#1810). |

Also in git: `ritz0/cat_ll`, a statically linked x86-64 **ELF binary** (from the Feb import `2d28304`, referenced by nothing), and `grammars/ritz.grammar.old` and `grammars/ritz1.grammar.old`.

**Fix:** delete the dead modules, the `.orig`, the `.old` files and the binary. Move `test_struct_layout.py` onto the live classes. Keep `symbol_table.py` for #1810. Add a liveness guard to `tools-unit`: every non-test `ritz0/*.py` must have a production importer or be on an explicit entry-point list.

### F2. The live emitter is one 12.4k-line class [architecture] — Major

`emitter_llvmlite.py` is 12,432 lines and `LLVMEmitter` starts at `:400`. Top functions:

| Function | Location | SLOC | Complexity |
|---|---|---|---|
| `_try_emit_simd_builtin` | `:8692` | 477 | 145 |
| `_emit_stmt_inner` | `:4247` | 358 | 119 |
| `_emit_expr` | `:5843` | 258 | 138 |
| `_emit_call_inner` | `:8342` | 215 | 93 |
| `_emit_method_call` | `:9752` | 213 | 97 |

102 functions nest 6 or more levels deep (10.5%; see metrics). The abandoned mixin split shows the intended shape. **Fix:** finish the split for real, one module per concern (exprs, stmts, calls, intrinsics/SIMD, patterns, layout), moving code rather than copying it, with F1's liveness guard preventing a second orphaned copy. SIMD and bitops intrinsics should become a table, not a 145-branch function.

### F3. The reference compiler's type checker is opt-in, and nothing opts in [architecture] — Major

`compile_file(..., check_types: bool = False)` at `ritz0.py:72`, `--check-names` / `--check-types` at `:357-361`. `grep -n "check-types\|check_types" build.py ritz0/test_runner.py tools/*.py scripts/*.sh` finds nothing, so no build, test or gate runs `type_checker.py` (1,079 lines) or `name_resolver.py`. Only the move checker is on. The oracle for ritz1 accepts whatever its emitter happens to lower. **Fix:** measure how many corpus/test programs fail under `--check-types`, fix the findings or the checker, and make it default-on. Don't leave a second quiet mechanism that asserts nothing.

### F4. The normative spec says `asm` and closures do not exist; ritz0 implements both and ritzlib uses `asm` [language-gap / spec drift] — Major

- `docs/LANGUAGE_SPEC.md:150`: "`asm` is reserved but has no syntax behind it yet."
- `ritz0/parser.py:1700-1730` parses `asm <arch>:` blocks with `{name}` operands.
- `ritzlib/testing.ritz:74` uses `asm x86_64:` (the test harness), and harland's `kernel/src/drivers/virtio/net.ritz` uses it too.
- `docs/LANGUAGE_SPEC.md:644`: closures are "Not implemented … the `|...|` form … never existed in the compiler".
- `ritz0/parser.py:1385-1405` parses `|x: i32| x * 2` expression closures; `emitter_llvmlite.py:7589` lowers them.
- The compile-gated examples only cover the error cases (`let asm = 1`, the block-bodied closure), so the gate cannot see the drift.

ritz1 has neither feature. That is why it hard-codes 14 syscall shims and cpuid as literal IR text (`ritz1/src/emitter.ritz:1081-1211`).

**Fix:** a LARB decision per feature. Either specify it (grammar, semantics, a positive compile-gated example) and give ritz1 parity, or remove it from ritz0 and port the users. `asm` is load-bearing for the kernel (harland), so specify it.

### F5. Duplicate infrastructure across compilers [architecture] — Minor

ritz0 and ritz1 each own a cache format at the same path (`emitter/fn_cache.py` vs `ritz1/src/fn_cache.ritz`, #1280 → #1807). Monomorph naming is string-based in ritz1, with `$`-separated components (`Result$T$E` → `Result$i32$E`, `ritz1/src/monomorph.ritz:966-970`). Spec §11.4 (`LANGUAGE_SPEC.md:1297-1299`) and ritz0 (`monomorph.py:90,123`) join arguments with `_` (`Result$i32_StrView`). Whether ritz1's *emitted* symbols diverge from §11.4 is unverified (needs a build). It goes in the monomorph ticket's acceptance criteria (ritz1.md).

## Not findings

- `parser.py` being hand-written while ritz1's parser is generated is a deliberate bootstrap choice. The defect is the *dead* generated parser beside it (F1), not the hand-written one.
- `async_transform_v2.py` being named `_v2` is ugly but live. Rename it when F1 deletes v1.

## Tickets

Epic **#1812**.

| Ticket | Pri | Finding |
|---|---|---|
| #1822 | 60 | F1: delete the dead code, repoint `test_struct_layout`, add a liveness guard |
| #1826 | 45 | F2: emitter split (after #1822) |
| #1823 | 65 | F3: type checker and name resolver on by default |
| #1825 | 70 | F4: specify `asm` and give ritz1 parity |
| #1623 | 45 | F4: closures spec drift (evidence appended) |
| #1807 | 90 | F5: sig files out of the source tree, one per compiler (absorbs #1280) |
