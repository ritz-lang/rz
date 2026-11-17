# ritz1 Architecture

ritz1 is the Ritz compiler written in Ritz. ritz0 (the Python bootstrap
compiler) builds it, and it then builds itself (`ritz1_selfhosted`). It
compiles one `.ritz` file to one LLVM IR `.ll` file; clang and ld do the rest.

**This document states no numbers.** A hand-written version said "11
source files, ~13,700 lines" for months after that stopped being true (AGAST
#1827), and a generated block committed here changed with every ritz1 commit,
so every two rooms editing ritz1 conflicted on it (#3896). Measure instead,
from `projects/ritz/`:

```bash
make arch-report    # modules, sizes, import graph and cycles, where each check runs, long functions
```

The gate (`make tools-unit`) holds this file to `tools/ritz1_arch.py
--check`: every module in `ritz1/src` has an entry under
[Module responsibilities](#module-responsibilities), every Sema check is in
its **Checks** list, and no module joins the import cycle. The script's
docstring states the rules and the counting rules; `tools/test_ritz1_arch.py`
pins them.

## Pipeline

`main.ritz` drives one compile. In order (`fn main` in `main.ritz`):

```
input.ritz
  │ fn_cache       check_source_unchanged: if the sig file records this source,
  │                this compiler and unchanged imports, reuse the .ll and stop
  ▼
[lex]       lexer_nfa scans tokens longest-match (lexer_scan_gen's generated
  │         keyword and operator matchers), tracking indentation
  ▼
[parse]     parser_gen (generated recursive descent) calls ast_helpers to
  │         build the AST (ast). Errors are located via diag.
  ▼
[imports]   main.resolve_imports: find each import next to the importer or on
  │         RITZ_PATH, lex+parse it (or read its cached interface text),
  │         strip it to its interface, merge it into the one Module.
  │         Re-parse once if type aliases / pending array lengths need it.
  ▼
[async]     async_lower: each `async fn` becomes ritz0's `<f>_Future` struct,
  │         constructor and `<f>_poll` state machine; every `await` is lowered;
  │         a bare call to an async fn is refused (§16.2)
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
the importer may instantiate, and for async fns (their locals lay out the
future the importer allocates), so a body-only edit to an import does not change
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
Sizes and imports are in `make arch-report`. Every module in `ritz1/src` has
an entry here, and every entry names a module that exists (`--check`).

**Front end**

| Module | Responsibility |
|---|---|
| `tokens_gen` | Token kinds and the `Token` struct. Generated from `grammars/ritz1.grammar`. |
| `lexer_nfa` | The lexer: a direct-coded scanner (longest match, a keyword beating an identifier of the same text), indentation and bracket tracking, string escapes. No NFA since #1821; the name stayed. |
| `lexer_scan_gen` | The grammar's keywords and operators as direct-coded matchers. Generated; ritzgen refuses a regex token `lexer_nfa` does not implement. |
| `parser_gen` | Recursive-descent parser. Generated. |
| `ast` | AST node structs (`Expr`, `Stmt`, `FnDef`, `StructDef`, `Module`, ...) and kind constants. |
| `ast_helpers` | AST constructors the grammar's actions call, the parser arena, type-alias and array-length folding, and AST queries used everywhere downstream. Hand-written (see below). |
| `diag` | Located diagnostics: one `<file>:<line>:<col>: error: <message>` line per error. |
| `async_lower` | `async fn` / `await` lowered, AST to AST, to ritz0's state machine (`<f>_Future`, `<f>`, `<f>_poll`; `async fn main` polled by a sync `main`), and a bare call to an async fn refused (§16.2). Run by main once, after imports merge. |
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

**Checks**

One entry per check module, sorted, with a blank line between entries, so
two rooms editing neighbouring entries touch no adjacent lines and git merges
them (#3896; `--check` enforces all three). An entry states the rule, not
where it runs: `make arch-report` says which checks are on Sema and which
still run mid-lowering on `*EmitterState`, and
`tools/ritz1_emitter_checks.allow` lists the emitter-side ones still to move
(#1816). A note that belongs to a move goes on that check's own entry.

- `binder_check` — a local can't take a module value's name, nor a name
  already in scope in its fn. Run by main over the whole module before
  monomorphisation.

- `bool_check` — `bool` is its own type: conditions and `and` / `or` / `not`
  take bool (LARB R4). `bool_kind` is the emitter's copy of its inference.

- `call_check` — a call's arguments fit its callee.

- `deref_field` — `.` through a struct's `Deref` / `DerefMut` (§7.7, R17).
  Sema also resolves such a `.` into step calls, each annotated
  (`Expr.deref_step`), before the other checks read the statement; the
  emitter only lowers them.

- `enum_as_int` — an enum value where an integer is expected (§10.4).

- `field_slot` — a struct-literal field given a struct of another type.

- `float_compare` — an f32 compared with an f64 asks for `as` (§7.2).

- `float_slot` — an integer into a float slot only where exact (§7.5).

- `generic_method` — a free call to a generic impl's method (R37, §5.4).

- `import_vis` — a plain `import` is private (§15.4, R54, #3891): a name
  that reaches the input only through another module's plain `import` is an
  error at its use. main records each loaded module and import edge before
  merging; `sema_walk` asks `vis_hidden` at each use in the input's own fns.

- `index_through` — `[]` through a pointer or reference (R9).

- `let_check` — `let` immutability: no write or `@&` through a `let`'s place.
  Its place rule (`let_place`) reads either view through a `LetEnv`:
  ref_check, still on the emitter, asks it about an `@x` of a `let`
  (`let_addr_of_own`).

- `literal_slot` — a literal takes its type from its slot (R3).

- `must_use` — a discarded call to a `[[must_use]]` fn (§17.8).

- `narrowing` — implicit narrowing in a typed let/var. Its rule is also read
  mid-lowering (float_slot, literal_slot, sizeof), from the emitter's own
  table of written types.

- `ownership` — move checking and drop insertion (§13).

- `pass_value` — `pass` has no value (§2.4, §6.1).

- `reachability` — code that can never run is refused. Run by main over the
  whole module before monomorphisation.

- `ref_check` — a reference doesn't fit a by-value slot, nor a value a
  reference slot, and an array only fits a slot of its own element type.

- `sema_index_store` — an index store ritz1 can't lower is refused, not
  miscompiled.

- `tail_value` — a `-> T` fn must not reach its end without a value. Its
  divergence walk (`tail_stmts_diverge`) is also read by `reachability` and
  `emitter_stmt`.

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
| `bool_kind` | The emitter's bool kind of an expression: bool_check's inference (`sema_bool_kind`), still read by codegen and the emitter-side checks. |
| `ll_copy_scan` | Text scan of emitted IR for large-struct copies (used by `emitter`'s rewrite pass). |
| `frame_limit` | Text scan of a fn's allocas: refuses a stack frame over 8 MiB at its largest local or temporary (#3739). |

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

Tracked under AGAST #1812 (M1.3). `make arch-report` shows its shape.

- **No semantic phase yet** — types are inferred during emission and most
  checks still run inside the emitter. Sema exists; the move is #1816.
- **The emitter import cycle** — the emitter modules, the emitter-side checks
  and monomorph form one strongly connected component (`make arch-report`,
  "Import cycles"), around `emitter_core`'s `EmitterState`. No module may
  join it (`CYCLE_BASELINE` in `tools/ritz1_arch.py`, checked by the gate).
  Breaking it, dissolving `emitter_core` and splitting the long functions
  the report lists is #1818.
- **Raw IR text** — the emitter writes IR as string fragments and re-parses
  its own output in post-passes (`ll_copy_scan`). A typed IR builder is #1817.
- **Duplicated type tables** — several type→LLVM/size/sign ladders; one
  `TypeRef` and one table is #1889.
- **C idioms** — `i32` flags for bool, `*u8`+length for names, kind codes
  as ints. #1820.
- **Grammar** — special-cased assignment forms and parser shape; #1819.
