# String Literal Migration Plan

*AGAST #90 deliverable. Analysis only; this document does not change any code.*

## 1. Current state

Ritz has three string-literal syntaxes:

| Syntax    | ritz0 (Python bootstrap)         | ritz1 (self-hosted)        |
| --------- | -------------------------------- | -------------------------- |
| `"..."`   | `String` (heap-owned)            | `*u8` (C-pointer, null-term.) |
| `c"..."`  | `*u8` (null-terminated)          | `*u8` *(today: bare and `c` collapse to one AST node; see CS1)* |
| `s"..."`  | `Span<u8>` (generic span)        | `StrView` *(design)* / `*u8` today |

Evidence:

* ritz0: `projects/ritz/ritz0/type_checker.py:332-344` — `StringLit` → `NamedType('String')`, `CStringLit` → `*u8`, `SpanStringLit` → `Span<u8>`.
* ritz1: `projects/ritz/ritz1/src/emitter_core.ritz:748-749` — `EXPR_STRING_LIT` → `TYPE_PTR` unconditionally; no separate AST tags for `c"/s"` yet (this is what CS1 / AGAST #89 fixes).
* `projects/ritz/ritzlib/strview.ritz:14` says the *intent* is that bare `"..."` produces `StrView`. Neither compiler implements that yet.

The design doc (`CLAUDE.md`) says:

```
"hello"  → String (heap-allocated)
c"hello" → *u8   (C string)
s"hello" → Span<u8> (zero-copy)
```

**The two compilers disagree** on what bare `"..."` means. Any code that
leans on either semantic will fail under the other. This is the core
problem the CS-series tasks exist to fix.

### Quantified footprint

Run `projects/ritz/tools/audit_string_literals.py`:

```
files scanned : 408
bare literals : 5,233     (c"..." / s"..." already-explicit excluded)

per project
  2,426  examples
  1,561  ritz1
    722  ritzlib
    495  ritz0
     24  test
      5  tests

per suggested prefix (heuristic)
  3,743  c           ~71%
  1,253  s           ~24%
    150  string      ~3%
     87  ?           ~2%
```

CSV evidence is checked in at `projects/ritz/docs/string_literal_audit.csv`
with columns `path,line,col,context,suggested_prefix`.

The 6,721 figure from the original survey includes `docs/archive/` (1,296
more bare strings in retired code that we deliberately skip). Scanning
live code only, the number is **5,233**.

## 2. Target state — opinionated

We recommend the following end state. Fence-sitting was not requested.

| Syntax    | Type          | Meaning                                       |
| --------- | ------------- | --------------------------------------------- |
| `c"..."`  | `*u8`         | Null-terminated C string. Primary FFI / syscall interop. Zero cost. |
| `s"..."`  | `StrView`     | Non-owning view: `{ ptr: *u8, len: i64 }`. Zero-alloc, explicit-length, UTF-8 assumed. The canonical Ritz string type. |
| `"..."`   | **banned**    | Rejected by the type checker. Authors pick a prefix. |

### Why ban bare `"..."`

1. **It is the source of the bug.** ritz0 and ritz1 cannot both be right
   about the default; any default we pick silently re-breaks half the
   codebase.
2. **The distinction is semantically important.** `*u8` is C-interop and
   null-terminated; `StrView` carries a length and plays with slicing;
   `String` owns memory. Inferring one of these from `"hi"` is a
   false economy — a one-character prefix tells the reader everything.
3. **We can migrate mechanically.** 97% of literals (c/s/string buckets
   in the audit) have an unambiguous preferred prefix from local
   context. Only ~2% need a human decision. A ban forces resolution of
   exactly those cases.
4. **Stdlib already leans this way.** `prints_cstr(*u8)` and
   `prints(StrView)` are distinct functions; the argument type already
   disambiguates. Adding the prefix brings the call site into sync.

### `s"..."` → `StrView`, not `Span<u8>`

ritz0 currently types `s"..."` as `Span<u8>` (the generic span); ritzlib
defines a purpose-built `StrView` in `strview.ritz`. `StrView` wins:

* Purpose-built. Methods like `strview_from_cstr`, `strview_len` are
  named for strings, not arrays.
* No monomorphization round-trip. Generic `Span<u8>` depends on the
  monomorphizer, which is the same feature blocking self-hosting.
* ritzlib's own design doc (`strview.ritz`) already calls `StrView`
  "the default string type for string literals".

We should add a trivial alias or conversion so existing `Span<u8>`
consumers keep working.

### `String` (owned)

No literal prefix. Owned strings always come from an explicit constructor
call (`string_from_cstr(c"hi")`, `string_from_strview(s"hi")`). This is
a deliberate choice: heap allocation should never be hidden behind a
literal.

## 3. Risk matrix — what breaks under each option

| Option                                 | What breaks                                                                                                                     | Fix cost         |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| (a) Ban bare `""` *(recommended)*      | Everything mentioning a bare string literal fails to compile until it is edited. 5,233 sites, ~97% scriptable, ~2% manual.      | High one-time; zero ongoing |
| (b) Default to `StrView`               | All of ritz1 + selfhosted breaks: bootstrap passes `"..."` as `*u8` to syscalls (305 hits in `ritzlib/sys.ritz` alone).          | ~3,743 C-argument sites need a `c""` rewrite *anyway* or an implicit `StrView` → `*u8` coercion (a footgun). |
| (c) Default to `*u8`                   | ritz0's existing passing tests break: anywhere the test relies on `String`-typed bare literals (~150 sites by the audit).       | Modest, but permanently hides allocation intent at literal sites. |
| (d) Default to `String` (heap)         | Every one of the 3,743 `*u8`-flowing sites allocates a heap `String`, then must still be cast to `*u8`. Catastrophic perf.      | Unacceptable.    |

Option (a) is the only one that brings the two compilers into permanent
agreement without a silent coercion that papers over the original bug.

## 4. Recommended migration sequence

The migration is *mostly* scriptable. The audit CSV gives every site,
its best-guess prefix, and enough context to batch-rewrite with
reasonable confidence.

### Phase 0 — land the audit (this task)

* `projects/ritz/tools/audit_string_literals.py` — scans, emits CSV
  to stdout, summary to stderr. Skips `c"..."` / `s"..."`, char
  literals, `#` comments, and `docs/archive/`.
* `projects/ritz/docs/string_literal_audit.csv` — committed snapshot
  (5,234 lines incl. header).

### Phase 1 — land CS1 (AGAST #89) first

Before any rewriting, ritz1 must distinguish `EXPR_CSTRING_LIT` and
`EXPR_SSTRING_LIT` at the AST/emitter level. Otherwise `c"..."` and
`s"..."` are indistinguishable from bare after rewrite. CS1 is the
mechanical precondition; this plan assumes it has landed.

### Phase 2 — scripted rewrite, low-risk directories first

Directory order, by risk/benefit:

1. **`examples/`** (2,426 sites). Isolated, well-tested, broken
   examples fail loudly and individually. Start here — it's where the
   tooling learns which heuristics are wrong. Within examples:
   * `tier1_basics/` — smallest, most-read, best first batch.
   * `tier2_stdlib/`, `tier3_coreutils/`, `tier4_applications/`.
   * `tier5_async/` last within examples (1,553 sites, highest density).
2. **`ritzlib/`** (722 sites). After examples prove the rewrite rules.
   `ritzlib/sys.ritz` alone is 305 sites — almost all `c""` (syscall
   argument paths).
3. **`ritz0/test/`** (495 sites). ritz0 tests — scripted rewrite, but
   keep one commit per test-file so a regression points at a single
   change.
4. **`ritz1/src/`** (1,388 sites) and **`ritz1/bootstrap_ritzlib/`**
   (90). The self-hosted compiler. Last, because:
   * It's the biggest cliff if a rewrite is wrong.
   * ritz1 itself currently treats bare as `*u8`; the audit's "c" bucket
     is already what ritz1 emits, so this phase is largely a
     `"..."` → `c"..."` textual substitution.
5. **`test/`, `tests/`** — trailing cleanup (29 sites total).

### Phase 3 — rewriter tool

Write a companion `projects/ritz/tools/apply_string_migration.py` that
reads the audit CSV and rewrites files in place, with these
guardrails:

* Only rewrites rows with a non-`?` suggested prefix.
* Re-verifies the literal at `(line, col)` still matches the CSV
  context before touching it (audit + patch may race; require a
  re-scan).
* Operates per-file atomically so each file is one diff.
* Emits a residual CSV of skipped `?` rows for human review.

### Phase 4 — manual pass on `?` rows

From the audit: **87 sites** (~2%) have no obvious prefix. These are
mostly `return "..."` sites and macro-like contexts where the callee's
expected type cannot be inferred locally. A human picks one and commits
per-file.

### Phase 5 — flip the type checker

Only once phases 2–4 are done do we change the compilers:

1. ritz0: `type_checker.py:332-335` — replace the `String` branch with
   a hard error: `bare string literals are not allowed; use c"..." or s"..."`.
2. ritz1: `emitter_core.ritz:748-749` — same, in the self-hosted
   emitter.

At this point the two compilers agree: bare `"..."` is a compile
error.

### Phase 6 — grep-based CI gate

Add a make target `make check-no-bare-strings` that runs the audit
script and fails CI if it finds any bare literals in tracked files
(excluding `docs/archive/`). Prevents regression.

## 5. Out of scope (explicit)

* Applying the migration — Phase 2 onward are separate AGAST tasks.
* Any change to `ritz0` or `ritz1` source — this task is analysis only.
* Changing `docs/archive/` content — retired, deliberately skipped.

## 6. File index

* `projects/ritz/docs/STRING_LITERAL_MIGRATION.md` — this plan.
* `projects/ritz/tools/audit_string_literals.py` — audit script.
* `projects/ritz/docs/string_literal_audit.csv` — current snapshot.

Regenerate the CSV at any time with:

```
python3 projects/ritz/tools/audit_string_literals.py \
    > projects/ritz/docs/string_literal_audit.csv
```
