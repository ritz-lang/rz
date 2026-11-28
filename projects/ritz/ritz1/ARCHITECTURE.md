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
its **Checks** list, and `ritz1/src` has no import cycle. The script's
docstring states the rules and the counting rules; `tools/test_ritz1_arch.py`
pins them.

## Pipeline

`main.ritz` drives one compile. In order (`fn main` in `main.ritz`):

```
input.ritz
  │ fn_cache       check_source_unchanged: if the sig file records this source,
  │                this compiler and unchanged imports, reuse the .ll and stop
  ▼
[lex]       lexer.ritz scans tokens longest-match (lexer_scan_gen's generated
  │         keyword and operator matchers), tracking indentation
  ▼
[parse]     parser_gen (generated recursive descent) calls ast_helpers to
  │         build the AST (ast). Errors are located via diag.
  ▼
[entry]     main_abi: check the file's `main` (§5.7); a Span main or one
  │         with no return type is renamed `__ritz_main` and gets the Ritz
  │         adapter `main(argc, argv, envp)`, parsed in as if written
  ▼
[imports]   main.resolve_imports: find each import next to the importer or on
  │         RITZ_PATH, lex+parse it (or read its cached interface text),
  │         strip it to its interface, merge it into the one Module.
  │         Re-parse once if type aliases / pending array lengths need it.
  ▼
[named]     named_variants: a struct variant's named pattern and literal
  │         become their positional forms (#4187)
  ▼
[async]     async_lower: each `async fn` becomes ritz0's `<f>$Future` struct,
  │         constructor and `<f>$poll` state machine; every `await` is lowered;
  │         a bare call to an async fn is refused (§16.2)
  ▼
[pre-mono checks]  impls on unknown/built-in types (main), binder_check,
  │                type_name_check, reachability — judged once per generic fn, used or not
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
instead of its source (`load_and_parse`, `fn_cache`); on a miss ritz1 stores
that text itself (`iface_text`).

## Where a new check goes

A semantic check (a rule that refuses a program) goes on **Sema**, never on
the emitter (AGAST #3462, #1816; LARB review/5 ritz1 N1):

- Write it as `pub fn <rule>_check(sm: *Sema, ..)` in its own module
  (`must_use.ritz` is the pattern).  It reads the AST only.  Use
  `sema_find_fn` / `sema_call_fn` / `sema_is_local` to resolve names, and
  `sema_error_at` to report a located `error: file:line:col: ...`.
- Read types from Sema, not the emitter (AGAST #3501).  `sema_find_local`
  gives a local's declared type (`SemaVar`), and `sema_expr_ty` /
  `sema_expr_type` (`sema_type.ritz`) type an expression, `TypeKind.Unknown` when
  Sema can't say: treat that as bool_check treats `BK_UNSURE`.  A bool is
  `TypeKind.Bool` there, not the emitter's i64 slot.  A shape your check needs
  that Sema leaves unknown goes into `sema_expr_ty` first, and
  `RITZ1_SEMA_PROBE=1` (`sema_probe.ritz`, pinned by
  `ritz0/test_ritz1_sema_type.py`) must still report no mismatch with the
  emitter's typing on the matrix corpus.
- Call it from the walk in `sema_walk.ritz`.  main runs `sema_check_module`
  after monomorphisation and before `emit_module`, over exactly the fns the
  emitter lowers, and stops on any error.
- Do not add a `pub fn *check*(s: *EmitterState, ..)`.
  `tools/test_ritz1_emitter_check_freeze.py` fails on a new one: every
  emitter-side check has moved (#1816), so the freeze is the grep being
  empty and its allowlist is deleted.
- Import no `emitter*` module (AGAST #3513).  A pure helper the emitter
  also uses (`name_eq`, `find_field_index`, `user_enum_index`, ...) lives in
  `ast_query`; move another one there rather than importing `emitter_core`.
  The same freeze test fails on a `sema*` module importing an emitter module,
  and on a Checks module doing so unless
  `tools/ritz1_check_emitter_imports.allow` names it (the modules still on
  `EmitterState`; that list only shrinks too).

## Module responsibilities

Each module's header comment is the authority on its rules; this is the map.
Sizes and imports are in `make arch-report`. Every module in `ritz1/src` has
an entry here, and every entry names a module that exists (`--check`).

**Front end**

| Module | Responsibility |
|---|---|
| `tokens_gen` | Token kinds and the `Token` struct. Generated from `grammars/ritz1.grammar`. |
| `lexer` | The lexer: a direct-coded scanner (longest match, a keyword beating an identifier of the same text), indentation and bracket tracking, string escapes. No NFA since #1821; renamed by #3887. |
| `lexer_scan_gen` | The grammar's keywords and operators as direct-coded matchers. Generated; ritzgen refuses a regex token `lexer` does not implement. |
| `parser_gen` | Recursive-descent parser. Generated. |
| `ast` | AST node structs (`Expr`, `Stmt`, `FnDef`, `StructDef`, `Module`, ...) and kind constants. |
| `ast_helpers` | AST constructors the grammar's actions call, the parser arena, type-alias and array-length folding, and AST queries used everywhere downstream. Hand-written (see below). |
| `ast_expr_syntax` | The grammar's expression actions: binary chains, casts, postfix, struct literals, numbers, match patterns, and the `TypeRef` the parser builds types into. Split from `ast_helpers` (AGAST #1818), which `pub import`s it. |
| `ast_type_syntax` | The grammar's type actions: fn-pointer types, type aliases, array-literal lengths, generic instance sites, tuple types. Split from `ast_helpers` (AGAST #1818), which `pub import`s it. |
| `ast_stmt_syntax` | The grammar's statement actions: inline assembly, lvalue assignment and the statement wrappers. Split from `ast_helpers` (AGAST #1818), which `pub import`s it. |
| `ast_query` | Pure queries over the AST, the enum tables and the type table (`name_eq`, `find_field_index`, `user_enum_index`, `mem_builtin_id`, ...): no `EmitterState`, no Sema. Moved out of `emitter_core` by #3513 so Sema and the checks import no emitter module; `emitter_core` `pub import`s it. Also the data-only types the Sema checks type their places from (`LocalVar`, `OwnPath`, `ArrayDims`) and the pure helpers that fill them (array dims, local placement, struct pointer levels), moved there by #4319 and #4391. |
| `types` | The one table of primitive type facts (AGAST #1889): LLVM spelling in memory and as a value, store size, alignment, bit width, signedness, Ritz name, name→kind. Struct/enum kinds answer "unknown"; the emitter's struct table sizes them. Also the one definition of the compiler-supplied `{ ptr, len }` view (AGAST #4545): `view_struct_new` builds it and `view_ptr_name` / `view_len_name` expose its field names, so the emitter's fallback, Sema's copy, monomorph's `Span<T>` template and `v[lo..hi]` lowering cannot drift. |
| `diag` | Located diagnostics: one `<file>:<line>:<col>: error: <message>` line per error, and the input-file global (`diag_source_file`, #4319) that locates them. |
| `async_lower` | `async fn` / `await` lowered, AST to AST, to ritz0's state machine (`<f>$Future`, `<f>`, `<f>$poll`; `async fn main` polled by a sync `main`), and a bare call to an async fn refused (§16.2). Run by main once, after imports merge. |
| `async_ast` | `async_lower`'s node builders and names: the AST nodes the lowering writes (`self.<field>`, `let`, `if`, a call, a generated fn) and the names it makes (`<f>$Future`, `<f>$poll`, `__poll_<k>`). Leaf code, reading only `ast`. |
| `named_variants` | A struct variant's named forms (§10.3, #4187): `V { b, a } =>` gets its bindings in field order and the literal `V { a: 1, b: 2 }` becomes the call `V(1, 2)`, in place, from the forms the parser noted (`named_form_note`); a missing, unknown or repeated field is refused at the name. Run by main once, after imports merge. |
| `interp` | Parses one `{expr}` placeholder of a print string: re-enters the lexer/parser for its text. Called by Sema (`call_check`, which notes each parse on its literal as `Expr.interp`) and by monomorphisation through `MonoCtx.interp_parse` (set by `main`); no emitter module reaches it (AGAST #4697). |
| `interp_text` | The placeholder text rules every pass shares: where a placeholder is (`interp_next_slot`, `interp_match_brace`), its spec, which call's literal is split (`interp_split_literal`), and Sema's parse noted on it (`interp_parsed_at`). Imports no parser, so the emitter reads placeholders through it (AGAST #4697). |

**Driver and caching**

| Module | Responsibility |
|---|---|
| `main_abi` | The program entry ABI (§5.7, AGAST #200): which shape `main` is, its three refusals, and the text of the adapter and span runtime (byte-identical to ritz0/main_abi.py). main.lower_main parses that text into the file's module before its fns are marked local. |
| `main` | CLI, the pipeline above, import resolution and merging, duplicate fn/const detection. |
| `fn_cache` | Sig file per source: a snapshot of emitted IR plus what it depends on; the no-op rebuild fast path. |
| `sha256` | SHA-256 for interface-text store keys shared with ritz0. |
| `iface_text` | The interface text an import is parsed from (`<t>.rzi.ritz`), built from the tokens on a miss, byte-identical to ritz0's (module_interface.interface_text), and stored atomically; fn_cache's sig records imports by it, so a body-only edit of an import keeps the fast path (AGAST #2113). |

**Generics**

| Module | Responsibility |
|---|---|
| `generic_infer` | Infers a generic call's type args from its arguments (LANGUAGE_SPEC §4.4). |
| `monomorph` | Specialises generic fns, structs and impls per instantiation. |
| `mono_clone` | Monomorphization's cloning: a generic fn, struct or impl method copied with its type parameters substituted. Nothing in `monomorph` calls it; `main` and the generic call sites import it (AGAST #1818). |
| `struct_index` | `[]` on a struct through `Index` / `IndexMut` / `IndexSet` (§7.8). |

**Checking phase (Sema)**

| Module | Responsibility |
|---|---|
| `sema` | The `Sema` context: typed scope, name lookup, error reporting. |
| `sema_type` | Types an expression from the AST and Sema's scope alone, including what `x[i]` holds (the through-index views' type facts, in `emitter_types` since #1818: a Vec, Span, String or `*[N]T` element, an `[N]*T` element's pointee). |
| `sema_walk` | Walks the module and calls each Sema check. |
| `sema_probe` | Test-only: compares Sema's typing with the emitter's (`RITZ1_SEMA_PROBE`). |
| `struct_cast` | `as` between two different struct types is refused (§7.5, LARB R72, #4000). |
| `wrapping` | `+%` / `-%` / `*%` are integer operators: a float or pointer operand is refused (LARB R63, §7.1, #3486). |
| `ptr_arith` | Pointer arithmetic is `*T ± int`, `int + *T` and `*T - *T`: any other arithmetic operand that is a pointer or reference is refused (§7.1, #4657). |
| `intrinsic_check` | The x86 / SIMD intrinsics' table: each one's arity and operand types, refused in ritz0's words (#4657). |

**Checks**

One entry per check module, sorted, with a blank line between entries, so
two rooms editing neighbouring entries touch no adjacent lines and git merges
them (#3896; `--check` enforces all three). An entry states the rule, not
where it runs: `make arch-report` says which checks are on Sema and which
still run mid-lowering on `*EmitterState`; the emitter-side ones are all
moved (#1816), and `tools/test_ritz1_emitter_check_freeze.py` holds the grep
empty. A note that belongs to a move goes on that check's own entry.

- `binder_check` — a local can't take a module value's name, nor a name
  already in scope in its fn. Run by main over the whole module before
  monomorphisation.

- `bool_check` — `bool` is its own type: conditions and `and` / `or` / `not`
  take bool (LARB R4). `bool_kind` is the emitter's copy of its inference.

- `call_check` — a call's arguments fit its callee: its count, each argument's
  kind, and what a pointer or array argument points at ("argument N of `f`
  has the wrong type", AGAST #4173), and what a bare argument to a `:&` param
  is (a temporary, a misfit, a place through an `@T`: AGAST #4244; the emitter
  keeps borrow_arg_kind only to lower a borrowed place to its address).

- `deref_field` — `.` through a struct's `Deref` / `DerefMut` (§7.7, R17).
  Sema also resolves such a `.` into step calls, each annotated
  (`Expr.deref_step`), before the other checks read the statement; the
  emitter only lowers them.

- `discarded_array` — an array field alone as a statement does nothing
  (#3189). Its receivers are typed by `deref_field`'s `df_member_field`.

- `enum_as_int` — an enum value where an integer is expected (§10.4).

- `field_slot` — a struct-literal field given a struct of another type.

- `float_compare` — an f32 compared with an f64 asks for `as` (§7.2).

- `float_slot` — an integer into a float slot only where exact (§7.5).
  Refused on Sema, which notes an exact unsigned source for the emitter's
  `uitofp` (`float_slot_unsigned`, #3510). `pointer_into_float` still runs
  mid-lowering (#3892).

- `fn_slot` — a fn value fits the fn-typed slot it lands in: arity, each
  param and the return, as ritz0's `_types_compatible` (#4310).  A global's
  fn signature and a fn type's `-> *T` / `-> @T` pointee are kept in the AST,
  so those slots are judged too (#4324).

- `generic_method` — a free call to a generic impl's method (R37, §5.4).

- `if_arm_value` — an if-expression arm must end in a value (§6.1, #1613), only where the value is wanted: a match statement's arms are statements (#3980).

- `impl_placement` — an `impl` lives in the type's file (or the trait's) and
  covers every instantiation, `impl<T> G<T>` (LARB R65, §12.2, #3494). Run by
  main after imports merge and before monomorphisation.

- `import_vis` — a plain `import` is private (§15.4, R54, #3891): a name
  that reaches the input only through another module's plain `import` is an
  error at its use. main records each loaded module and import edge before
  merging; `sema_walk` asks `vis_hidden` at each use in the input's own fns.
  Over the same tables, `vis_selective_check` refuses a name in the input's
  `import m { … }` that `m` doesn't define, at the name (§15.1, R54, #3467),
  once imports are resolved and before any later pass.

- `index_refuse` — what has nothing to index or no pointer to follow (§7.8,
  R9; #3893): `p[i]` through an `@T` that isn't a buffer, `x[i][j]` /
  `(*p)[i]` of a scalar or a struct without `Index`, `*v` of a value, a whole
  array stored into `p[i]`. On Sema, its locals typed as the emitter's
  (`rs_local`), at every index and `*` the walk visits.

- `intrinsic_check` — the AES-NI, SHA-NI, `simd_add` / `simd_xor` /
  `simd_rotl` and `xgetbv` intrinsics as one table (#4657): each one's arity,
  its operands' names and what they must be (a v4i32, a v2i64, a vector).
  A call that breaks its row is refused at the call, in ritz0's words; an
  operand Sema can't type is left to the emitter.

- `let_check` — `let` immutability: no write or `@&` through a `let`'s place.
  Its place rule (`let_place`) reads either view through a `LetEnv`:
  `ref_value` asks it about an `@x` of a `let` in an `@&T` slot
  (`let_addr_of_own`).

- `literal_slot` — a literal takes its type from its slot (R3). Run on Sema
  (#3510), it annotates the AST for the emitter: a `"..."` in a `*u8` slot
  becomes `c"..."`, and a `/` / `%` records its wider slot (`Expr.slot_type`).

- `must_use` — a discarded call to a `[[must_use]]` fn (§17.8).

- `narrowing` — implicit narrowing in a typed let/var (§7.5). Its rule is also read
  mid-lowering (sizeof), from the emitter's own table of written types;
  float_slot and literal_slot read it on Sema (`narrow_sema_*`, #3510).

- `no_effect` — an expression statement whose value is discarded must do
  something (§6.6, LARB R64, #3492): a literal, name, field, index, borrow,
  `*p`, cast, aggregate literal or operator is refused with its source text;
  `pass` and a whole array place are not this rule's. LARB R69 (#3968,
  #3997): the value of a non-value block's tail and of a statement `if` /
  `match` arm is discarded too, so a do-nothing arm is `_ => pass`.

- `own_check` — the move check (§13, #2158), on Sema since #3507: a use
  of a moved value, a move out of a reference, an array element or a global,
  a `:&` param's referent read by value, and a deferred statement checked at
  each exit it runs on. sema_walk calls its `own_check_*` hooks where the
  emitter used to, so the move state flows through the same steps (`if` and
  arm merges, loop shadows, `defer` replays at every exit, match ownership).
  Its errors wait until the walk ends and print only if no other check
  failed. It annotates each fn with the bindings that own a move-only value
  (`FnDef.own_binds`), which `ownership` gives drop flags.

- `ownership` — drop insertion (§13.6): drop flags, the moves that clear
  them, glue, temporaries and `defer` lowering. Which bindings own a value is
  Sema's annotation (`FnDef.own_binds`); the check itself is `own_check`'s.
  Each `ret`'s drops are emitted with it, for what is live there (#3508):
  nothing rescans the finished body for them.

- `pass_value` — `pass` has no value (§2.4, §6.1).

- `ptr_arith` — pointer arithmetic is `*T ± int`, `int + *T` and `*T - *T`
  (§7.1, #4657); any other `+ - * / %` with a pointer or reference operand
  is refused at that operand, in ritz0's typing pass's words. An `@T` local
  under `+` / `-` is the emitter's `refuse_ref_arith`'s (#3037).

- `reachability` — code that can never run is refused. Run by main over the
  whole module before monomorphisation.

- `ref_check` — the reference queries both sides ask; its checks have all
  moved to Sema: §13.5 borrow conflicts to `ref_loan` (#3506), the rest to
  `ref_value` (#3926, #4011). Its place queries (`ref_ty_in`, `ref_view_in`,
  `ref_write_is_shared_in`, `ref_temp_call_in`) are one copy over a `RefEnv`,
  the emitter's locals or Sema's scope; on Sema a binding is read from the
  image of the `LocalVar` the emitter will make for it (`RsNote.loc`). It
  keeps Sema's place typing (`rs_ty`) and per-binding notes (`RsNote`), and
  what the emitter still asks (`ref_ty_of`, `ref_through`, `ref_temp_call`).

- `ref_loan` — a borrow of a place conflicts with an overlapping loan
  (§13.5, R11 / R11a). A loan ends with its holder's block: Sema's blocks
  and match arms (`ref_loan_enter` / `ref_loan_leave`), not the emitter's
  scopes. A place's steps are typed from Sema's scope and notes (`rs_ty`);
  what Sema can't type borrows nothing.

- `ref_value` — `@T` is read-only (§13.3, R1): no write, `@&` or `self: @&T`
  receiver through an `@T`; a reference to a local doesn't leave its fn
  (§13.5, R2). And the slot checks (§13.2-13.4, R1, R5, R42): a reference
  doesn't fit a by-value slot, nor a value a reference slot, nor `@x` or an
  `@T` an `@&T` / `:&` one; an array only fits a slot of its own element
  type and length; a call's temporary isn't a place; `[v; n]` of a move-only
  v. Its places are typed by `ref_check`'s `RefEnv` queries.

- `sema_index_store` — an index store ritz1 can't lower is refused, not
  miscompiled.

- `slot_kind` — a value whose kind doesn't fit its slot is refused at a
  `let` / `var`, an assignment, a struct literal field, a `return` and a fn's
  tail (#4653): a struct into a scalar or pointer, a scalar, `null` or
  pointer into a struct, a float or `null` into an integer, an int narrower
  than i64 / u64 to or from a pointer. The rule is call_check's
  `slot_kind_fit`, which a call's argument asks too (`cc_kind`: a named fn's
  scalar misfits since #4680, as ritz0 judges no method's); this module says
  it in ritz0's words for each slot. A generic instance's `*T` field carries
  its substituted pointee kind (monomorph's `subst_pointee_field`), so the
  rule sees `w.ptr` as the `*Point` it is.

- `slot_narrowing` — the same rule at an assignment, a call argument, a
  `return`, a fn's tail value (§7.5, #4081) and a struct literal field
  (#4218), on Sema, at the slots literal_slot visits; a tail is judged where
  the walk reaches it, with its block's `let`s and its arm's bindings in scope.

- `struct_cast` — `as` between two different struct types, by value or
  through a reference, is a located refusal at the `as` (§7.5, LARB R72,
  #4000): build the other struct from the fields. `r as C` with `r` an `@C` /
  `@&C` / `*C` reads a copy of the referent (#3004), and `@c as *D` is a
  pointer cast; both stay legal.

- `struct_variants` — same-named structs (§15.3, §17.2, #4111): the parser
  notes every struct, `[[target_os]]`-filtered or not, with its target and a
  hash of its tokens; after imports resolve, two differing definitions that
  always coexist (no gate, or one target), or a gated one beside an ungated
  one on its own target, are "Conflicting struct definition" as in ritz0.
  Two files' are twins, `type_twins`'s; enums and aliases are noted for it.

- `tail_value` — a `-> T` fn must not reach its end without a value. Its
  divergence walk (`tail_stmts_diverge`) is also read by `reachability` and
  `emitter_stmt`.

- `trait_bound` — a type parameter's bound `<T: A + B>` (§11.5, LARB R55,
  #3469): an unknown trait at the bound, and each of monomorph's instances
  (fn, struct, enum, and a generic impl's on its type) needing an impl of
  each trait, exact or through a generic impl, at the argument as first
  written (ast_helpers' `GenericUse` notes) or the inferred call.

- `type_name_check` — a written type name must name a type: "unknown type
  `Nope`" at the name (#3932). Run by main over the whole module before
  monomorphisation; `type_named` records where each name was written.

- `type_twins` — types follow the fn rule (§15.3, #4609): two definitions of
  one struct, enum or alias name conflict only in a module that sees both
  (`import_vis`), in ritz0's words; otherwise the one the input doesn't see
  is renamed `Name__<hash>` by the second parse pass in the files that see
  it, its methods keep their `T_m` symbols, and a bare variant is judged over
  the enums its file sees.

- `wrapping` — `+%` / `-%` / `*%` wrap an integer: a float or a pointer
  operand is refused where the source wrote the operation (LARB R63, §7.1,
  #3486). The parser keeps the plain operator with `Expr.wrapping` set, so
  every other pass reads it as `+`.

**Emitter**

| Module | Responsibility |
|---|---|
| `emitter` | `emit_module`, `emit_fn`, impl methods; post-passes over the emitted IR text. |
| `emitter_consts` | Module-level data: global initializers, integer const resolution, const arrays of struct literals, scalar struct consts. Split from `emitter` (AGAST #1818), which `pub import`s it. |
| `emitter_core` | `EmitterState` and its four parts (AGAST #4697: `IrBuf` the module's IR and what it must define at its tail, `FnCtx` the fn being emitted, `SymTab` the module's symbols, `Diag` what was reported), struct-aware type→LLVM mapping over `types`, local/struct/fn lookup, IR text helpers, member-access GEPs. Imports no emitter module above it (AGAST #1818), so it sits below the emission modules: a fn that needs one belongs in `emitter_types`. |
| `emitter_types` | What an expression's type, struct, pointee or element is, asked before it is emitted: the expression typing the old `emitter_core` did, the through-index views (the old `index_through`), and the method-callee and deref-pointee lookups (AGAST #1818). It reaches no emission module, so it and the Sema-side checks that read it sit below the emission modules. |
| `emitter_abi` | How a struct or array crosses a call: sret returns and byval params (AGAST #1730, #1739, #2306, #3181), their attributes, and the deferred large-struct loads and copies. Above `emitter_core`, below the emitter modules (AGAST #1818). |
| `emitter_call_lower` | The call path's parts that never recurse into `emit_expr`: argument and receiver place facts, arg conversions, `sizeof`, enum payload shapes, builtin method pieces, the `CALL_INTRINSICS` table. Below the emission modules (AGAST #1818). |
| `emitter_decl` | `let` / `var` typing and placement: what a declaration's slot is (the `decl_infer_*` phases, the `infer_*_let` views), tuple bindings. Below the emission modules (AGAST #1818). |
| `emitter_stmt_parts` | Statement lowering that never recurses into a statement or expression: `for` headers and element slots, if / match arm phi types, array and N-D row copies. Below the emission modules (AGAST #1818). |
| `ir_operand` | What the text of an IR operand says: the digits of a register after `%.`, and whether it is the base of a GEP or the pointer of a load / store. The decisions behind the `format_into` sink, on StrViews alone so a unit test states them (AGAST #4696). A leaf module. |
| `text_bridge` | The older `*u8` text APIs read as StrViews: the `(out_name, out_len)` lookups (`named_by`), C-string LLVM type spellings (`llvm_text`). A ported file calls these instead of carrying a `*u8`; each goes when the API it reads is ported (AGAST #4696). |
| `emitter_ir` | Typed IR builders (casts, load/store, alloca, branches): the spelling of an instruction lives here, not at each site. A leaf module, so it stays below the emission modules (AGAST #1817). |
| `emitter_seam` | The emit table's wrappers (`emit_expr`, `emit_stmt`, `emit_lvalue_ptr`, `emit_member_ptr`, `emit_expr_into_slot` / `_into_field`, `emit_expr_method`, `emit_array_local_whole_assign`): each a call through `EmitterState.emit` (`EmitTable` in `emitter_core`), which `emit_module` wires to the `*_impl` fn doing the work. Statements and expressions nest, so emission recurses; it recurses through here, not through imports, and the emission modules below form no cycle (AGAST #4697). Imports only `emitter_core`. |
| `emitter_expr_access`, `emitter_print`, `emitter_match`, `emitter_try`, `emitter_aggregate`, `emitter_expr`, `emitter_expr_arith`, `emitter_expr_call`, `emitter_dispatch`, `emitter_stmt` | The emission modules, in import order: each imports only those before it, and `emitter_seam` for the rest (AGAST #4697). Identifiers / index / member (and the n-d index pointers, spills, struct copies); the `print` builtin, byte-identical to ritz0's output; `match` lowered to an if-else chain; the try operator `x?`, its payload's address for an array store (AGAST #4918); array and struct values written into a place (literals, fills, array-valued `if` / `match` / blocks); member pointers and casts; binary / unary and places; calls and methods; `emit_expr`'s switch over `ExprKind`; statements: declarations, assignment, control flow, `for`. |
| `emitter_asm` | `asm` blocks to LLVM inline asm. |
| `bool_kind` | The emitter's bool kind of an expression: bool_check's inference (`sema_bool_kind`), still read by codegen and the emitter-side checks. |
| `frame_limit` | Text scan of a fn's allocas: refuses a stack frame over 8 MiB at its largest local or temporary (#3739). |

### Generated vs hand-written

Three modules carry the `# Generated by ritzgen` header and are regenerated
from `grammars/ritz1.grammar` by `tools/ritzgen_py/ritz_generator.py`;
`make -C projects/ritz regen-check` fails if a committed copy drifts.
`ast_helpers` is hand-written: the generator writes only a stub listing the
constructor names the grammar's actions call, so there is no generated copy
of it to compare.

## Emitter style

ritz1 is written in Ritz, so its emitter reads as Ritz: `emitter_expr_arith` is the
reference, and every emitter file follows what it does (AGAST #4695, #4696; #4766
ported the last one and deleted the old shim).  The old form was one call per
fragment of NUL-terminated `c"..."` text, with a `*u8` for every type name; what
is left of it (`c""` literals, `*u8` parameters) is pinned down-only per file
(`tools/ritz1_text_ratchet.py`, run by `make tools-ratchets`).

**Where the IR goes.** One `Arena` per emitted module (`main.ritz` opens it and
frees it with the module).  `EmitterState.ir.out` is a `String` drawn from it, as is
the entry-block alloca buffer, each sized once to the room it has (`arena_string`):
they never grow, so no block is ever realloc'd or freed on its own, which keeps
the compile valgrind-clean.  An IR that outgrows its buffer stops the compile with
a message; it is never written truncated.

**How text goes in.** The state is itself the `format_into` sink
(`EmitterState.push_bytes`): a whole instruction is one call, text is a `StrView`
literal, and values are interpolated.

```text
# before: five calls, a `*u8` per fragment
emit_str(s, IR_INDENT)
emit_reg(s, left_as_ptr)
emit_str(s, IR_INTTOPTR)
emit_reg(s, left_reg)
emit_str(s, c" to ptr\n")

# after: the instruction, as it is written in the IR
format_into(s, "  %.{left_as_ptr} = inttoptr i64 %.{left_reg} to ptr\n")
```

The sink is where IR text becomes IR: a piece that starts a `ret` drops the live
owned bindings first, and the digits after `%.` are a register operand, noted as
used by the deferred struct loads and the packed-align tracking.  So `%.{r}` is a
register.  A piece with no value in it that a lookup returned (a type spelling) is
written with `emit_sv(s, ty)`, which runs the same `ret` hook.

**Rules for a ported file.**

1. No `c"..."`: a `c""` belongs only at a C boundary, which an emitter file has
   none of.  The fragment shim (`emit_str`, `emit_reg`, `emit_int`, `emit_label`)
   and its `IR_*` fragments are gone; don't bring them back.
2. No `*u8` (or `**u8` out-parameter) in a signature: a name or a type spelling is
   a `StrView`; a message is a `String` built with `format_into(@&msg, "...")`.  A
   lookup that still speaks `*u8` is read through `text_bridge`.
3. An opcode, predicate or type that depends on a kind is a `match` returning a
   `StrView`, not a ladder of `emit_str` arms:

```text
# before: twenty arms, each a call
OpKind.Div =>
    if uns == 1
        emit_str(s, c"udiv i64 ")
    else
        emit_str(s, c"sdiv i64 ")

# after: the table, then one line that uses it
OpKind.Div => if unsigned then "udiv i64 " else "sdiv i64 "
...
let opcode: StrView = int_binop_opcode(e.op, unsigned, shr_u != 0)
format_into(s, "  %.{result} = {opcode}%.{left_reg}, %.{scaled_right}\n")
```

   A port simplifies the logic as well as the text. Each case is decided once, in one
   place (`docs/STANDARD.md` S-MATCH-3, `docs/REVIEW.md` A11). The rule has three parts:
   - **No dead arms.** A case handled by an earlier `return` has no arm in a later
     table. `emit_expr_binary` returns early for `And`/`Or`, so `int_binop_opcode`
     lists them with the operators that can't reach it.
   - **No repeated guards.** Test a shared condition once and nest the checks.
   - **No catch-all output.** A table from an enum to IR text lists every variant.
     The variants with no output return `no_name()`, and the caller reports a
     located error. A `_` is fine only when it means "none of these" (`false`,
     `None`, `pass`).

```text
# before: `And` can't get here, and an operator the table forgets is an add
OpKind.And | OpKind.BitAnd => "and i64 "
...
_ => "add i64 "
if (e.op == OpKind.Eq or e.op == OpKind.Ne) and refuse_pointer_strlit_eq(s, e)
    return 0
if (e.op == OpKind.Eq or e.op == OpKind.Ne) and refuse_tagged_enum_eq(s, e)
    return 0

# after: each case once; an unexpected operator is an error
OpKind.Add => "add i64 "
OpKind.BitAnd => "and i64 "
...
OpKind.Unset | OpKind.And | OpKind.Or | OpKind.Neg | ... => no_name()
if e.op == OpKind.Eq or e.op == OpKind.Ne
    if refuse_pointer_strlit_eq(s, e) or refuse_tagged_enum_eq(s, e) or ...
        return 0
```

4. Yes/no is a `bool`; a status plus an out-parameter is an `Option` (or a struct);
   a refusal reason is an `enum` with a text `match` (`Trap` in `emitter_expr_arith`).
5. A struct type behind `getelementptr %` is opened with `gep_struct_open` (the
   packed-struct check lives in `emit_name`); any other IR name is `ir_name(n)`.
6. Behaviour is the contract: `make ritz1-bootstrap` builds the compiler, and
   `tools/ritz1_ir_identity.py --ref <reference ritz1> --cand build/ritz1` (and the
   `ritz1_selfhosted` pair) compares the `.ll` of every module of ritz0/test,
   ritzlib and ritz1/src.  The reference is built from the commit before the port.
   A port that is not meant to change the IR changes none of it.

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
- **The emitter import cycle** is gone (AGAST #4697): #1818 took
  `emitter_core`, the typing (`emitter_types`) and the checks out of it,
  and #4697 broke the last seven modules' cycle with one dispatch seam
  (`emitter_seam`, the emit table). `CYCLE_BASELINE` in
  `tools/ritz1_arch.py` is empty, so the gate refuses any new cycle.
  Dissolving `emitter_core` and splitting the long functions the report
  lists is #1818's remainder.
- **Raw IR text** — the emitter writes IR as string fragments and re-parses
  its own output in post-passes (the packed-align and frame-limit scans). A
  typed IR builder is #1817.
- **Duplicated type tables** — several type→LLVM/size/sign ladders; one
  `TypeRef` and one table is #1889.
- **C idioms** — `i32` flags for bool, `*u8`+length for names, kind codes
  as ints. #1820.
- **Grammar** — special-cased assignment forms and parser shape; #1819.
