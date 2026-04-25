# Profile: ritz1 self-compile bottleneck

**TL;DR**: `lexer_match_from` accounts for **98.79%** of all instructions when
ritz1 compiles a typical source file. The function does an O(transitions) linear
scan of every NFA edge on every recursive step. Fixing it (per-state transition
index) should make ritz1's per-file compile time drop from ~12 s to ~1-2 s,
collapsing a 4-5 minute selfhost rebuild to under a minute.

---

## How I profiled

```
cd projects/ritz/ritz1
RITZ_PATH=/home/aaron/dev/ritz-lang/rz/projects/ritz \
  valgrind --tool=callgrind \
    --callgrind-out-file=/tmp/callgrind.out \
    --separate-callers=2 \
    ./build/ritz1 src/emitter.ritz -o /tmp/emit.ll
callgrind_annotate /tmp/callgrind.out
```

Target file: `ritz1/src/emitter.ritz` — 1700 lines, the largest ritz1 source.
Wall time native: 12.4 s. Wall time under callgrind: 10 m 43 s (~50× overhead,
typical for callgrind).

---

## The result (top-line)

```
PROGRAM TOTALS                              62,866,993,598 instructions

98.79%  lexer_nfa.ritz : lexer_match_from   (62,106,459,108 Ir)
 0.82%  lexer_nfa.ritz : lexer_match_from   (518,375,251 Ir, fewer-recursive callers)
```

**One function. ~99% of all instructions.** Everything else combined — parser,
emitter, monomorphization, file I/O — is under 1% of runtime.

`lexer_match_from` was called **5,078,850 times** during this single compile.

---

## Why it's slow (annotated)

`projects/ritz/ritz1/src/lexer_nfa.ritz:175`:

```ritz
fn lexer_match_from(lex: *Lexer, state: i32, pos: i64, ...) -> i32
  ...
  # Try epsilon transitions
  for i in 0..nfa.trans_count                    # ← 24.72% of all instructions
    let trans_ptr: *Transition = nfa.transitions + i   # ← 24.82%
    if trans_ptr.from_state == state_i64 and trans_ptr.kind == TR_EPSILON
      lexer_match_from(lex, trans_ptr.to_state as i32, pos, ...)
  ...
  # Try character transitions
  for i in 0..nfa.trans_count                    # ← 24.72% of all instructions
    let trans_ptr: *Transition = nfa.transitions + i   # ← 24.79%
    if trans_ptr.from_state == state_i64 and trans_matches(trans_ptr, ch) == 1
      lexer_match_from(lex, trans_ptr.to_state as i32, pos + 1, ...)
```

The two inner `for i in 0..nfa.trans_count` loops together are **~99% of
runtime**. Each loop:

- Iterates **all** transitions in the NFA (`MAX_TRANS = 512`, but the actual
  Ritz NFA has hundreds of edges).
- Filters by `trans_ptr.from_state == state_i64` to find ones leaving the
  current state.
- A typical NFA state has 1-5 outgoing edges; the rest of the iterations are
  pure waste.

The waste compounds with recursion depth (epsilon transitions recurse into
`lexer_match_from` again, which again scans all transitions).

For `emitter.ritz`:
- Source ≈ 50,000 characters
- ~5 million invocations of `lexer_match_from`
- Each invocation does ~2 × 400 = 800 transition checks (estimated)
- Result: ~4 billion transition comparisons. **Most of them go to states that
  weren't even the current state.**

---

## The fix

Build a per-state transition index at NFA load time. The data structure change:

```ritz
struct NFA
  states: *NFAState
  state_count: i64
  transitions: *Transition       # sorted by from_state after nfa_finalize
  trans_count: i64
  start_state: i64
  # NEW: per-state outgoing-transition window
  state_trans_offset: *i32       # state_id → start index in `transitions`
  state_trans_count: *i32        # state_id → number of outgoing transitions
```

Add a `nfa_finalize(nfa)` step called after all transitions are added but
before lexing begins:

1. Sort `transitions` in place by `from_state` (counting sort works — there
   are bounded states, ~hundreds).
2. Walk the sorted list once and fill the `(offset, count)` table per state.

Replace the hot loops in `lexer_match_from`:

```ritz
let state_start: i32 = *(nfa.state_trans_offset + state)
let state_count: i32 = *(nfa.state_trans_count + state)

# Epsilon transitions for THIS state only
for i in state_start..(state_start + state_count)
  let trans_ptr: *Transition = nfa.transitions + i
  if trans_ptr.kind == TR_EPSILON
    lexer_match_from(lex, trans_ptr.to_state as i32, pos, ...)

# Character transitions for THIS state only
for i in state_start..(state_start + state_count)
  let trans_ptr: *Transition = nfa.transitions + i
  if trans_ptr.kind != TR_EPSILON and trans_matches(trans_ptr, ch) == 1
    lexer_match_from(lex, trans_ptr.to_state as i32, pos + 1, ...)
```

The inner loop is now `O(outgoing transitions of this state)` (typically 1-5)
instead of `O(total NFA transitions)` (typically 400+).

**Expected speedup**: 50-100×. ritz1 compile time per file drops from ~12 s to
~0.2-0.5 s. Selfhost rebuild drops from ~3 m to ~10-20 s.

---

## Estimated effort

- `nfa.ritz`: add struct fields, `nfa_finalize` (sort + index build) — ~80 LoC
- `lexer_nfa.ritz`: replace two inner loops — ~10 LoC
- Wire `nfa_finalize` call into `lexer_setup_gen.ritz` after all
  `nfa_add_*_trans` calls — ~5 LoC
- Update `.sig` files (auto-regenerated)

**~100 LoC total**, contained to two files plus one call site.

Risk: medium. The change is purely a data-structure optimisation — semantics
are identical. But because `lexer_match_from` is on the hot path of every
ritz1 invocation, a bug here would break **every** test. Validation level 3
(`make matrix-full`) is the right gate before merging.

---

## Other observations from the profile

- `trans_matches` (NFA edge type/range check) is called via the second loop
  but is itself trivial — 0.13% of total. It's the *number of times* it gets
  called that's the problem, not the function itself.
- All other functions (parser, emitter, monomorph) are below the 1% threshold
  combined. The compiler is bottlenecked entirely on lexing.
- ritz0 (Python) doesn't have this problem because it uses CPython's `re`
  module — a heavily optimised native regex engine — for tokenisation.

---

## Decision needed

The fix is well-scoped and the payoff is large:

| Metric | Before | After (estimated) |
|---|---|---|
| ritz1 / file | 12 s | 0.2-0.5 s |
| `make bootstrap` (selfhost) | 3 m 6 s | 10-30 s |
| `make matrix-full` total | ~5 min | ~1.5 min |

**Recommendation**: schedule as the next focused session. It pays for itself
across every future iteration. Defer until then — don't bolt it onto an
unrelated change.

---

## Attempted implementation, 2026-04-25 — blocked on a sibling bug

Built and tested the per-state index in nfa.ritz + lexer_nfa.ritz +
generator change to `setup_lexer` signature.  The optimisation itself works
exactly as expected:

| Metric | Before | After (measured) |
|---|---|---|
| ritz1 self-compile of `emitter.ritz` | 12.4 s | **0.336 s** |
| `make matrix` (ritz1-only) | ~30 s | **11 s** |

**~37× speedup on ritz1, validated end-to-end.**

But selfhost (`ritz1_selfhosted`) failed: when ritz1 self-compiles the new
nfa.ritz, the resulting binary's `lexer_match_from` emits `load i8` from a
pointer that should be `load i64` — the local-pointer-deref counterpart of
the `d30466f` fix (which only handled global pointers).

The relevant LL fragment for the new code:

```llvm
; ritz1 sees `let off: i64 = *(nfa.state_trans_offset + state_i64)`
%.105 = mul i64 %.104, 8       ; ✓ correct stride for *i64
%.106 = inttoptr i64 %.103 to ptr
%.107 = getelementptr i8, ptr %.106, i64 %.105
%.108 = ptrtoint ptr %.107 to i64
%.109 = inttoptr i64 %.108 to ptr
%.110 = load i8, ptr %.109     ; ✗ should be `load i64`
```

ritz1's pointer arithmetic correctly uses stride 8, but the subsequent
load width defaults to i8.  The pointee type is lost across the
`inttoptr/ptrtoint` round-trip.  Same shape of bug as `d30466f` (where
globals' pointee type was tracked in `GlobalVarDef.pointee_type`); the
local-binding equivalent (`LocalVar.pointee_type`?) doesn't exist yet.

I tried widening the index arrays to `*i64` (since i64 stores work — the
write side hits a different codegen path that does honour the type). That
fixed the writes during finalize, but reads in `lexer_match_from` still
got `load i8` because the read path is what's broken.

**Reverted the Tier 1 attempt.**  The optimisation is correct; ritz1's
codegen for typed-local-pointer reads is the actual blocker.

### Prerequisite for landing Tier 1

Extend ritz1's emitter to track pointee type for local pointer bindings:

1. Add `pointee_type: i32` to `LocalVar` (mirror of `GlobalVarDef.pointee_type`)
2. In `find_local_type` / equivalent, propagate pointee_type for `*T` locals
3. In `emit_expr_arith` and `emit_expr` (OP_DEREF), when reading
   `*(local_ptr + i)`, look up the local's pointee_type and emit the
   correct load width
4. Apply the same to OP_DEREF on a struct-field access whose field type
   is `*T`

Estimated effort: ~80-120 LoC across ast.ritz / ast_helpers.ritz /
emitter_core.ritz / emitter_expr_arith.ritz.  Sibling of `d30466f` —
should be tractable in one focused session.

After that lands, re-applying Tier 1 NFA optimisation is a ~30-line cherry
pick: the previous attempt branched on `regen-check + matrix-full` and is
recoverable from `git reflog`.  Validation gate is `make matrix-full`.
