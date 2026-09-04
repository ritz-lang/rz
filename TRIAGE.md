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

## Open

4. **discovery.ritz StrView\*** — `TypeError: Type of #2 arg mismatch:
   %"struct.ritz_module_1.StrView"* != %"struct.ritz_module_1.StrView"`.
   Question: is this the #1290 auto-borrow gap (by-value struct passed where
   callee expects `*T`, codegen fails to auto-take address —
   known case `vec_get$Point2D`)? Diagnosis in progress — first diagnostic
   agent lost to a permission-prompt stall (AGAST #1337).
   NOTE: a sibling `Option` failure may hide behind this one in discovery.ritz.
