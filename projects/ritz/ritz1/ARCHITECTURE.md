# ritz1 Architecture

ritz1 is the Ritz compiler written in Ritz. ritz0 (the Python bootstrap
compiler) builds it, and it then builds itself (`ritz1_selfhosted`). It
compiles one `.ritz` file to one LLVM IR `.ll` file; clang and ld do the rest.

**Numbers in this document are generated.** The block under
[Measurements](#measurements) is the output of `tools/ritz1_arch.py`, and the
prose outside it states no counts. The previous version of this file was
written by hand and said "11 source files, ~13,700 lines" for months after
that stopped being true (AGAST #1827). To refresh it, from `projects/ritz/`:

```bash
python3 tools/ritz1_arch.py --write ritz1/ARCHITECTURE.md   # regenerate
python3 tools/ritz1_arch.py --check ritz1/ARCHITECTURE.md   # exit 1 if stale
```

The counting rules (what a "code line", an "import" and a "function" are) are
in the script's docstring and pinned by `tools/test_ritz1_arch.py`.

## Pipeline

`main.ritz` drives one compile. In order (`fn main` in `main.ritz`):

```
input.ritz
  │ fn_cache       check_source_unchanged: if the sig file records this source,
  │                this compiler and unchanged imports, reuse the .ll and stop
  ▼
[lex]       lexer_setup_gen registers the token patterns; lexer_nfa runs them
  │         (nfa + regex) longest-match, tracking indentation
  ▼
[parse]     parser_gen (generated recursive descent) calls ast_helpers to
  │         build the AST (ast). Errors are located via diag.
  ▼
[imports]   main.resolve_imports: find each import next to the importer or on
  │         RITZ_PATH, lex+parse it (or read its cached interface text),
  │         strip it to its interface, merge it into the one Module.
  │         Re-parse once if type aliases / pending array lengths need it.
  ▼
[pre-mono checks]  impls on unknown/built-in types (main), binder_check,
  │                reachability — judged once per generic fn, used or not
  ▼
[monomorph] generic_infer fills in type args from call arguments;
  │         monomorph specialises generic fns/structs and (with
  │         struct_index) rewrites `m[k]` on a struct into its Index call
  ▼
[sema]      sema_walk runs the checks registered on Sema (sema, sema_type,
  │         must_use, generic_method, field_slot, ...) over exactly the
  │         fns the emitter will lower. Any error stops here.
  ▼
[emit]      emitter.emit_module lowers each fn to IR text through the
  │         emitter_* modules, still running the checks that have not yet
  │         moved to Sema (see "Known structural debt")
  ▼
output.ll   + a sig file (fn_cache) for the next run's fast path
```

### Imports: declare vs define

Imports are not inlined. `parse_program` marks every fn parsed from the input
file `is_local = 1` before imports are merged; imported fns stay
`is_local = 0`. The emitter `define`s local fns and `declare`s imported ones,
so each `.ll` holds only its own file's bodies plus the `linkonce_odr`
monomorph instantiations it needs. Each import is cut to its interface as it
loads (`strip_to_interface`): bodies are kept only for generic fns and methods
the importer may instantiate, so a body-only edit to an import does not change
the importer's IR. An import may be read from its cached interface text
instead of its source (`load_and_parse`, `fn_cache`).

## Where a new check goes

A semantic check (a rule that refuses a program) goes on **Sema**, never on
the emitter (AGAST #3462, #1816; LARB review/5 ritz1 N1):

- Write it as `pub fn <rule>_check(sm: *Sema, ..)` in its own module
  (`must_use.ritz` is the pattern).  It reads the AST only.  Use
  `sema_find_fn` / `sema_call_fn` / `sema_is_local` to resolve names, and
  `sema_error_at` to report a located `error: file:line:col: ...`.
- Read types from Sema, not the emitter (AGAST #3501).  `sema_find_local`
  gives a local's declared type (`SemaVar`), and `sema_expr_ty` /
  `sema_expr_type` (`sema_type.ritz`) type an expression, `TYPE_UNKNOWN` when
  Sema can't say: treat that as bool_check treats `BK_UNSURE`.  A bool is
  `TYPE_BOOL` there, not the emitter's i64 slot.  A shape your check needs
  that Sema leaves unknown goes into `sema_expr_ty` first, and
  `RITZ1_SEMA_PROBE=1` (`sema_probe.ritz`, pinned by
  `ritz0/test_ritz1_sema_type.py`) must still report no mismatch with the
  emitter's typing on the matrix corpus.
- Call it from the walk in `sema_walk.ritz`.  main runs `sema_check_module`
  after monomorphisation and before `emit_module`, over exactly the fns the
  emitter lowers, and stops on any error.
- Do not add a `pub fn *check*(s: *EmitterState, ..)`.
  `tools/test_ritz1_emitter_check_freeze.py` fails on a new one.  Its
  allowlist (`tools/ritz1_emitter_checks.allow`) lists the checks still in
  the emitter.  The list only shrinks: each move off the emitter is a child
  ticket of #1816 and deletes its entries.

## Module responsibilities

Each module's header comment is the authority on its rules; this is the map.
Sizes and imports are in [Measurements](#measurements).

**Front end**

| Module | Responsibility |
|---|---|
| `tokens_gen` | Token kinds and the `Token` struct. Generated from `grammars/ritz1.grammar`. |
| `nfa`, `regex` | Thompson-construction NFA engine, and the regex parser that builds NFAs from pattern strings. |
| `lexer_nfa` | Multi-pattern lexer: longest match, first-definition priority, indentation and bracket tracking, string escapes. |
| `lexer_setup_gen` | Registers the grammar's token patterns with the lexer. Generated. |
| `parser_gen` | Recursive-descent parser. Generated. |
| `ast` | AST node structs (`Expr`, `Stmt`, `FnDef`, `StructDef`, `Module`, ...) and kind constants. |
| `ast_helpers` | AST constructors the grammar's actions call, the parser arena, type-alias and array-length folding, and AST queries used everywhere downstream. Hand-written (see below). |
| `diag` | Located diagnostics: one `<file>:<line>:<col>: error: <message>` line per error. |
| `interp` | Reads `{expr}` placeholders in print strings; re-enters the lexer/parser for each placeholder expression. |

**Driver and caching**

| Module | Responsibility |
|---|---|
| `main` | CLI, the pipeline above, import resolution and merging, duplicate fn/const detection. |
| `fn_cache` | Sig file per source: a snapshot of emitted IR plus what it depends on; the no-op rebuild fast path. |
| `sha256` | SHA-256 for interface-text store keys shared with ritz0. |

**Generics**

| Module | Responsibility |
|---|---|
| `generic_infer` | Infers a generic call's type args from its arguments (LANGUAGE_SPEC §4.4). |
| `monomorph` | Specialises generic fns, structs and impls per instantiation. |
| `struct_index` | `[]` on a struct through `Index` / `IndexMut` / `IndexSet` (§7.8). |

**Checking phase (Sema)**

| Module | Responsibility |
|---|---|
| `sema` | The `Sema` context: typed scope, name lookup, error reporting. |
| `sema_type` | Types an expression from the AST and Sema's scope alone. |
| `sema_walk` | Walks the module and calls each Sema check. |
| `sema_probe` | Test-only: compares Sema's typing with the emitter's (`RITZ1_SEMA_PROBE`). |
| `must_use`, `generic_method`, `field_slot` | Checks already moved onto Sema. |
| `binder_check`, `reachability` | Whole-module checks run by main before monomorphisation. |

**Checks still called from the emitter**

`bool_check`, `call_check`, `deref_field`, `enum_as_int`, `float_slot`,
`index_through`, `let_check`, `literal_slot`, `narrowing`, `ownership`
(move checking and drop insertion), `ref_check`, `tail_value`. Each header
cites its rule. They take `*EmitterState` and run mid-lowering; moving them
to Sema is #1816's work.

**Emitter**

| Module | Responsibility |
|---|---|
| `emitter` | `emit_module`, `emit_fn`, impl methods; post-passes over the emitted IR text. |
| `emitter_core` | `EmitterState`, type→LLVM mapping, local/struct/fn lookup, IR text helpers, member-access GEPs. |
| `emitter_expr` | `emit_expr` dispatch and struct literals. |
| `emitter_expr_access`, `emitter_expr_arith`, `emitter_expr_call` | Identifiers/index/member; binary/unary; calls and methods. |
| `emitter_stmt` | Statements: declarations, assignment, control flow, `for`. |
| `emitter_match` | `match` lowered to an if-else chain. |
| `emitter_print` | The `print` builtin, byte-identical to ritz0's output. |
| `emitter_asm` | `asm` blocks to LLVM inline asm. |
| `ll_copy_scan` | Text scan of emitted IR for large-struct copies (used by `emitter`'s rewrite pass). |

### Generated vs hand-written

Three modules carry the `# Generated by ritzgen` header and are regenerated
from `grammars/ritz1.grammar` by `tools/ritzgen_py/ritz_generator.py`;
`make -C projects/ritz regen-check` fails if a committed copy drifts.
`ast_helpers` is hand-written: the generator writes only a stub listing the
constructor names the grammar's actions call, so there is no generated copy
of it to compare.

## Build

`ritz1/Makefile`. Each `src/*.ritz` compiles to its own `build/*.ll`
(ritz0, `--no-runtime`) and `build/*.o` (clang `-O2`). ritzlib objects come
from the shared artifact store (`cas.py get-or-build`). `ld` links them with
`runtime/ritz_start.x86_64.o`; no libc. `mkdeps.py` writes each module's
transitive imports to `build/*.d`, so a struct change rebuilds every
importer. `make bootstrap` repeats the build with `build/ritz1` as the
compiler to produce `build/ritz1_selfhosted`.

## Known structural debt

Tracked under AGAST #1812 (M1.3). The measurements below show its shape.

- **No semantic phase yet** — types are inferred during emission and most
  checks still run inside the emitter. Sema exists; the move is #1816.
- **The emitter import cycle** — the emitter modules, the emitter-side checks
  and monomorph form one strongly connected component (see Import cycles),
  around `emitter_core`'s `EmitterState`. Breaking it, dissolving
  `emitter_core` and splitting the long functions listed below is #1818.
- **Raw IR text** — the emitter writes IR as string fragments and re-parses
  its own output in post-passes (`ll_copy_scan`). A typed IR builder is #1817.
- **Duplicated type tables** — several type→LLVM/size/sign ladders; one
  `TypeRef` and one table is #1889.
- **C idioms** — `i32` flags for bool, `*u8`+length for names, kind codes
  as ints. #1820.
- **Lexer** — runtime NFA built per file with recursive backtracking; a
  generated scanner is #1821.
- **Grammar** — special-cased assignment forms and parser shape; #1819.

## Measurements

<!-- BEGIN generated by tools/ritz1_arch.py -->

`ritz1/src/` has **47** modules, **78839** lines (**58531** code lines, excluding blanks and comments), **2632** functions and **288** local import edges. 3 modules (10791 lines) are generated by ritzgen: `lexer_setup_gen`, `parser_gen`, `tokens_gen`.

### Modules in dependency order

Every module appears after all the modules it imports (modules in a cycle are adjacent). `(gen)` marks generated modules.

| Module | Imported by | Lines | Code | Local imports |
|---|--:|--:|--:|---|
| `fn_cache` | 1 | 1074 | 717 | — |
| `ll_copy_scan` | 2 | 143 | 107 | — |
| `nfa` | 5 | 408 | 262 | — |
| `regex` | 1 | 269 | 169 | nfa |
| `sha256` | 1 | 192 | 175 | — |
| `tokens_gen` (gen) | 12 | 149 | 121 | — |
| `ast` | 38 | 944 | 490 | tokens_gen |
| `diag` | 7 | 84 | 36 | ast |
| `lexer_nfa` | 5 | 1105 | 709 | nfa, regex, tokens_gen |
| `ast_helpers` | 35 | 7727 | 5524 | ast, diag, lexer_nfa, tokens_gen |
| `lexer_setup_gen` (gen) | 2 | 120 | 105 | lexer_nfa, nfa, tokens_gen |
| `parser_gen` (gen) | 2 | 10522 | 8510 | ast, ast_helpers, tokens_gen |
| `interp` | 1 | 153 | 102 | ast, ast_helpers, lexer_nfa, lexer_setup_gen, nfa, parser_gen, tokens_gen |
| `struct_index` | 5 | 249 | 180 | ast, diag |
| `binder_check` | 4 | 371 | 277 | ast, ast_helpers, emitter_core |
| `bool_check` | 11 | 691 | 581 | ast, ast_helpers, emitter_core, emitter_expr_call, index_through, let_check |
| `call_check` | 1 | 401 | 278 | ast, ast_helpers, bool_check, diag, emitter_core, emitter_expr_call |
| `deref_field` | 6 | 924 | 745 | ast, ast_helpers, emitter_core, emitter_expr_call, ref_check, struct_index |
| `emitter_asm` | 2 | 529 | 433 | ast, ast_helpers, emitter_core |
| `emitter_core` | 30 | 6397 | 4207 | ast, ast_helpers, deref_field, index_through, ownership, ref_check, tokens_gen |
| `emitter_expr` | 9 | 2926 | 2207 | ast, ast_helpers, bool_check, emitter_core, emitter_expr_access, emitter_expr_arith, emitter_expr_call, emitter_match, emitter_stmt, float_slot, index_through, literal_slot, ownership, ref_check, sema_probe, struct_index, tokens_gen |
| `emitter_expr_access` | 4 | 1968 | 1560 | ast, ast_helpers, deref_field, emitter_core, emitter_expr, emitter_expr_arith, index_through |
| `emitter_expr_arith` | 4 | 2278 | 1755 | ast, ast_helpers, bool_check, emitter_core, emitter_expr, emitter_expr_access, emitter_expr_call, emitter_stmt, index_through, literal_slot, narrowing, ownership, ref_check |
| `emitter_expr_call` | 12 | 7251 | 5555 | ast, ast_helpers, binder_check, bool_check, call_check, emitter_core, emitter_expr, emitter_expr_access, emitter_expr_arith, emitter_print, emitter_stmt, float_slot, index_through, let_check, literal_slot, monomorph, narrowing, ownership |
| `emitter_match` | 3 | 2517 | 1849 | ast, ast_helpers, bool_check, deref_field, emitter_core, emitter_expr, emitter_expr_access, emitter_expr_call, emitter_print, emitter_stmt, enum_as_int, float_slot, let_check, monomorph, narrowing, ownership, tokens_gen |
| `emitter_print` | 4 | 1185 | 984 | ast, ast_helpers, bool_check, emitter_core, emitter_expr, emitter_expr_call, interp, lexer_nfa |
| `emitter_stmt` | 6 | 6982 | 5108 | ast, ast_helpers, binder_check, bool_check, deref_field, emitter_asm, emitter_core, emitter_expr, emitter_expr_arith, emitter_expr_call, emitter_match, emitter_print, enum_as_int, float_slot, index_through, let_check, literal_slot, narrowing, ownership, ref_check, tail_value, tokens_gen |
| `enum_as_int` | 3 | 234 | 169 | ast, ast_helpers, emitter_core, emitter_expr_call, emitter_match, let_check, narrowing |
| `float_slot` | 4 | 117 | 74 | ast, ast_helpers, bool_check, diag, emitter_core, narrowing |
| `index_through` | 10 | 640 | 462 | ast, ast_helpers, emitter_core, emitter_expr, struct_index |
| `let_check` | 7 | 538 | 397 | ast, ast_helpers, emitter_core, emitter_expr_call |
| `literal_slot` | 5 | 493 | 399 | ast, ast_helpers, bool_check, emitter_core, index_through, narrowing |
| `monomorph` | 4 | 4575 | 3274 | ast, ast_helpers, diag, emitter_core, struct_index |
| `narrowing` | 8 | 585 | 444 | ast, ast_helpers, emitter_core |
| `ownership` | 8 | 3817 | 3024 | ast, ast_helpers, emitter_core, emitter_expr, emitter_expr_call, emitter_stmt, index_through, ll_copy_scan, ref_check |
| `ref_check` | 7 | 2456 | 1941 | ast, ast_helpers, deref_field, emitter_core, emitter_expr_call, index_through, let_check, ownership |
| `sema` | 5 | 213 | 136 | ast, ast_helpers, diag, emitter_core |
| `sema_probe` | 3 | 157 | 114 | ast, ast_helpers, bool_check, emitter_core, sema, sema_type |
| `sema_type` | 2 | 197 | 151 | ast, ast_helpers, emitter_core, sema |
| `tail_value` | 3 | 265 | 174 | ast, ast_helpers, emitter_core |
| `emitter` | 1 | 3831 | 2735 | ast, ast_helpers, bool_check, deref_field, emitter_asm, emitter_core, emitter_expr, emitter_print, emitter_stmt, enum_as_int, let_check, literal_slot, ll_copy_scan, narrowing, ownership, ref_check, tail_value, tokens_gen |
| `generic_infer` | 1 | 1166 | 965 | ast, ast_helpers, diag, monomorph |
| `generic_method` | 1 | 72 | 45 | ast, ast_helpers, emitter_core, sema |
| `field_slot` | 1 | 83 | 58 | ast, ast_helpers, emitter_core, sema, sema_type |
| `must_use` | 1 | 44 | 17 | ast, ast_helpers, emitter_core, sema |
| `reachability` | 1 | 202 | 139 | ast, ast_helpers, binder_check, emitter_core, tail_value |
| `sema_walk` | 1 | 208 | 164 | ast, ast_helpers, emitter_core, field_slot, generic_method, must_use, sema, sema_probe, sema_type |
| `main` | 0 | 1470 | 961 | ast, ast_helpers, binder_check, emitter, fn_cache, generic_infer, lexer_nfa, lexer_setup_gen, monomorph, nfa, parser_gen, reachability, sema_probe, sema_walk, sha256, struct_index, tokens_gen |

### Import cycles

1 import cycle (strongly connected components of more than one module):

- 26 modules: `binder_check` ↔ `bool_check` ↔ `call_check` ↔ `deref_field` ↔ `emitter_asm` ↔ `emitter_core` ↔ `emitter_expr` ↔ `emitter_expr_access` ↔ `emitter_expr_arith` ↔ `emitter_expr_call` ↔ `emitter_match` ↔ `emitter_print` ↔ `emitter_stmt` ↔ `enum_as_int` ↔ `float_slot` ↔ `index_through` ↔ `let_check` ↔ `literal_slot` ↔ `monomorph` ↔ `narrowing` ↔ `ownership` ↔ `ref_check` ↔ `sema` ↔ `sema_probe` ↔ `sema_type` ↔ `tail_value`

### ritzlib modules imported

14 ritzlib modules, each with the number of ritz1 modules importing it: `fmt` (1), `gvec` (10), `hash` (5), `hashmap` (5), `io` (31), `json` (1), `memory` (17), `option` (1), `os.env` (2), `span` (1), `str` (12), `string` (3), `strview` (3), `sys` (36).

### Long functions

16 functions longer than 300 code lines:

| Function | Module:line | Code lines |
|---|---|--:|
| `emit_stmt_inner` | `emitter_stmt:5888` | 785 |
| `emit_var_decl_at` | `emitter_stmt:1211` | 776 |
| `emit_expr_call` | `emitter_expr_call:4213` | 748 |
| `emit_expr_index` | `emitter_expr_access:759` | 728 |
| `emit_expr_method` | `emitter_expr_call:6130` | 727 |
| `parse_primary_expr` | `parser_gen:8946` | 674 |
| `parse_assign_stmt` | `parser_gen:6388` | 635 |
| `emit_assign` | `emitter_stmt:2543` | 533 |
| `emit_member_ptr_at` | `emitter_expr:484` | 418 |
| `parse_type_spec` | `parser_gen:2753` | 396 |
| `parse_global_var_def` | `parser_gen:2300` | 366 |
| `parse_impl_block` | `parser_gen:10106` | 358 |
| `emit_for_iterable` | `emitter_stmt:4023` | 357 |
| `emit_lvalue_ptr` | `emitter_expr_arith:1558` | 354 |
| `parse_let_stmt` | `parser_gen:4772` | 354 |
| `emit_expr_binary` | `emitter_expr_arith:225` | 332 |

<!-- END generated by tools/ritz1_arch.py -->
