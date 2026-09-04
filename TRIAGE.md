# Task 1321 — triage of 8 concealed angelo compile failures

WIP enumeration notes. Squashed/removed before final; parent squashes on reap.

## Classified

1. **`?`-on-MethodCall trio** — ritz0 type-inference bug. `_infer_ritz_type`
   cannot infer the type of a static-method-call binding
   (`var reader = Reader.new(...)`), so the receiver has no recorded type when
   `?` later needs it. One-line-family fix verified via runtime monkeypatch
   against all three real files. Corpus grep: shape is angelo-only in practice.
   → Fix in ritz0 here + regression test (no separate ticket).

2. **font.ritz `outline`** — angelo bug. Nested variant pattern
   `Ok(Simple(outline))` — construct the language doesn't support (zero corpus
   usage). → Fix: two-level match in angelo + "nested patterns unsupported"
   diagnostic in ritz0.

3. **tests.ritz `Option`** — ritz0 gap. let/var path passes the raw generic
   name to enum lookup while the assignment path resolves it properly.
   Mechanical fix, mirrors existing code.

## Classified (cont.)

4. **discovery.ritz StrView\*** — CONFIRMED same defect *class* as #1290
   (auto-borrow gap: value passed where callee expects pointer), but a
   *sibling site*, not the identical code path:
   - `_emit_call` (~7313): has the rvalue-spill fallback (`arg.tmp`) but only
     triggers auto-borrow for ritz-level RefType/mutable-borrow params —
     misses `*T` PtrType-expected params → the #1290 `vec_get$Point2D` shape.
   - `_emit_method_call` (~8746): triggers on the right condition (LLVM
     pointer-typed param) but on unaddressable args fell back to emitting the
     struct BY VALUE → the discovery.ritz crash.
   FIXED: method-call fallback now spills rvalue args to an entry-block
   alloca (mirrors receiver path and `_emit_call`). Verified: StrView*
   mismatch gone; discovery.ritz progresses to next error.
   TODO: regression test in ritz0/tests; check whether same trigger-condition
   fix in `_emit_call` closes #1290 proper (separate ticket unless trivial).

5. **discovery.ritz sibling (was hidden)** — `IndexError: tuple index out of
   range` in `_emit_enum_match` (~9547) GEP for `data_index`: enum matched
   with tag-only/unspecialized layout — same class as tests.ritz raw generic
   `Option` name gap (item 3). Confirms the predicted hidden Option failure.

## Post-cascade findings (discovery/font/interpreter fully peeled)

The "8 failures / 4 classes" triage was the *first layer*. Peeling revealed
the full defect graph — final tally 12 distinct defects:

**ritz0 defects (fixed here, each with regression tests):**
- Auto-borrow rvalue args, `_emit_method_call` arm (item 4) — 6c80cdd, 711907d
- Auto-borrow rvalue args, `_emit_call`/#1290 arm — 1261578 (separate commit,
  revertable; parent closes #1290 at merge)
- Synthesized Option/Result specializations: ad-hoc layout (align:=size,
  placeholder payloads) disagreeing with the shared layout helper → 6f7d325.
  Item 5's real root — NOT the item-3 class as first suspected.
- Static-style UFCS calls rejected (`String.from` → `string_from`) — 1d49997
- Nested-pattern located diagnostic (item 2 deliverable) — df08623
- Expected-enum threading: if/match arm tails, block tails, and
  `_emit_assign_expr` (arm-position assignments) — df08623
- Match on method-call scrutinee: identified-struct-type fallback — df08623
- Match phi over ir.Undefined (mixed value/assignment-tail arms) — df08623

**angelo fantasy-API defects (angelo-side rewrites):**
- `String.concat` → push_strview; `Vec.clone` → `[:]` (ritzlib gap filed as
  AGAST #1338); `vec pop as Option` → emptiness guard; `rfind`/`to_lowercase`/
  `char_at`-on-StrView/u8 case predicates → agent adding ritzlib fns +
  rewrites (discovery.ritz, subpixel.ritz)
- font.ritz nested pattern → two-level match (df08623)

**Still open (agent-owned):** item 1 (?-trio: cmap/hmtx/loca), item 3
(tests.ritz raw-generic Option let/var path).

## FINAL — full defect enumeration for reap attribution (rebased hashes)

The ticket's "8 failures / 4 classes" was two layers deep in a 19-defect
stack. Every fix below revealed the next; none were visible at triage time.

### ritz0 compiler defects (14)
 1. `_emit_method_call` rvalue auto-borrow gap (StrView* mismatch) — `77d8b26`+tests `46a276d`
 2. `_emit_call` `*T` PtrType auto-borrow gap (#1290 sibling arm) — `abf1820`
 3.   ...predicate over-broad for `*u8` byte-buffer params (found via ritzlib
      fs.ritz regression; struct-pointee restriction) — `dc8eeed`
 4. Synthesized Option/Result specializations: ad-hoc layout diverged from
    shared `_enum_variant_field_layout` → IndexError GEP — `c61ee15`
 5. Static-style UFCS calls (`String.from` → `string_from`) rejected — `5e60d40`
 6. Nested variant patterns: silent misbind → located diagnostic naming the
    construct with fix-it hint — `eb357a0`
 7. Expected-enum threading missing through if/match arm tails and
    arm-position assignments (`_emit_assign_expr`) — `eb357a0`
 8. Match-on-method-call scrutinee: identified-struct fallback — `eb357a0`
 9. Undefined-incoming phi guard (statement matches w/ void arms) — `eb357a0`
10. `_infer_ritz_type`: static-method-call bindings (`var r = Reader.new()`)
    uninferrable → `?` failed on cmap/hmtx/loca — `88de08c`
11. let/var generic enum annotation passed raw name (`Option`) — `978ef2f`
12. `ritz_types` never scoped per function → stale-binding wrong dispatch
    (metrics: FontMetrics vs Option<GlyphMetrics>) — `4f651d0`
13. Tuple-type mangling embedded source span → `Result<(), E>` split into
    distinct types per written-at site, invalid ret IR — `17fdb19`
14. Unit fns emitted `ret %Struct` for non-i32 tails — `166a19d`
15. Mixed-type statement-match phi (enum value + dummy i32 0) — `ccf4396`
16. `==`/`!=` on aggregates emitted icmp on structs → located diagnostic
    w/ strview_eq/string_eq hint — `7c511f7`
17. Match arms leaked `has_returned` → function tail suppressed, empty
    unterminated merge block — `fa663bb`
18. `llvm.floor/ceil/round` lower to libm libcalls (no libc!) → inline
    fptosi/sitofp+select lowering; first corpus user — `f3120ef`

### ritzlib gaps (angelo called never-existing API)
 - `strview_rfind` — `85a93dd`; `strview_to_lower`/`string_to_lower` —
   `c2bf930`; `string_eq_strview` — `dcec4fc` (all with direct tests,
   separate commits per parent condition)
 - `vec_clone<T>` — FILED as AGAST #1338 (angelo uses `[:]` idiom instead)
 - corpus-wide fantasy-API sweep — FILED as AGAST #1339 (not run here)

### angelo source defects
 - nested `Ok(Simple(x))` patterns (font.ritz) → two-level match — `eb357a0`
 - fantasy stdlib calls in discovery/subpixel → real API — `0244ced`
 - `==` on StrView (instructions.ritz, zero corpus usage) → strview_eq — `7c511f7`
 - duplicate `test_rasterize_with_antialiasing` symbol (tests.ritz vs
   render.ritz) → renamed — `f3120ef`

### Gate results (rebased onto f336bae)
 - ritz0 pytest: 762 passed, 8 skipped, 3 xpassed, 0 failed
 - make matrix-full (clean ritz1/build): 53/53 × 3
 - angelo: builds, both configured binaries run exit 0
   (NOTE: ritz.toml defines TWO binaries — angelo-test, simple-test — not three)
 - rz.toml: angelo removed from [ci.known_failing.build]
 - regression.sh + rz build --all: see reap callback
