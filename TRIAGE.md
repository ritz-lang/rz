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
