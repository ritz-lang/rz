# Enum Variants

**Status**: design accepted, implementation in progress (AGAST #1282)
**Applies to**: ritz0 (Python bootstrap) and ritz1 (self-hosted)

This document specifies the three declaration forms for enum variants, the
memory layout they share, and the pattern-matching rules that bind their
payloads. It also records the central design decision — *struct-style variants
are sugar, not a distinct kind* — together with the alternative that was
rejected.

---

## 1. The three forms

```ritz
pub enum BrowserToTabMsg
    # (a) bare / unit variant — no payload
    Stop

    # (b) tuple variant — positional payload
    Reload(i32)

    # (c) struct variant — named payload, indented block
    SetViewport
        width: u32
        height: u32
```

All three are the same construct with different amounts of syntax. A variant
has an ordered list of payload fields; the forms differ only in whether that
list is empty, written positionally, or written with names.

### Why an indented block rather than braces

Ritz is indentation-based, and every *declaration* in the language already
introduces its members with an indented block — `struct`, `trait`, `impl`, and
the enum body itself. Struct variants follow that rule, so a struct variant's
field block is lexically identical to a `struct` field block:

```ritz
struct Viewport          pub enum Msg
    width: u32               SetViewport
    height: u32                  width: u32
                                 height: u32
```

Braces were considered and rejected *for declarations*. Note that this is not
an argument that braces are un-Ritzy in general: `Point { x: 1, y: 2 }` is
already the struct **literal** syntax. The split is deliberate and consistent —

| Position | Syntax | Precedent |
|---|---|---|
| Declaring fields | indented block | `struct`, `trait`, `impl` |
| Constructing a value | `Name { field: value }` | struct literals |

so a struct variant declares like a `struct` and (optionally, see §4)
constructs like one. Importing Rust's `Navigate { url: String }` *declaration*
form would have been the only brace-delimited declaration block in the
language.

---

## 2. Decision: named fields are sugar

> **A struct variant is a tuple variant whose fields also have names.**

`SetViewport { width: u32, height: u32 }` and `SetViewport(u32, u32)` produce
**the same tag, the same payload layout, and the same ABI**. The names are
retained in the AST for pattern matching, construction, diagnostics and
metadata, but they do not create a new kind of variant and they do not change a
single byte of the emitted representation.

Consequences:

- Positional patterns work on struct variants: `SetViewport(w, h)`.
- Named patterns work (§4) and are the recommended form for 3+ fields.
- Field **order** is significant, because it defines the payload layout.
  Reordering fields in a declaration is an ABI break, exactly as it is for a
  `struct`.

### Rationale

1. **The codebase already assumes it.** `projects/tempest/lib/ipc.ritz`
   declares struct-style variants while `lib/tab_renderer.ritz:100` matches
   them positionally (`Navigate(url)`, `SetViewport(width, height)`). Under the
   sugar reading, tempest compiles as written on both sides. Nothing had ever
   compiled this code, so the inconsistency was never reconciled; sugar
   reconciles it in the direction that requires no rewrite.
2. **Precedent in this repo.** AGAST #1285 made `[T]` sugar for `Span<T>`
   rather than introducing a parallel slice type. Same instinct: prefer a
   surface form that lowers onto an existing representation over a second
   representation that must be kept in sync forever.
3. **Two compilers must agree.** Ritz is self-hosting; every representational
   choice has to be implemented twice and stay bit-identical. Sugar has no
   representation of its own, so there is nothing to diverge. A distinct kind
   would double the layout, construction and match-lowering surface in both
   ritz0 and ritz1.
4. **It is the smaller change.** Under sugar, `Variant.fields` stays a
   positional `List[Type]` and gains an optional parallel list of names. Every
   existing consumer — layout, monomorphization, metadata, match lowering —
   keeps working untouched.

### Rejected alternative: struct variants as a distinct kind

Under this reading, `SetViewport { .. }` could only be matched by naming its
fields; `SetViewport(w, h)` would be a type error, and the compiler would track
"tuple variant" and "struct variant" as separate cases through every pass.

It is arguably cleaner — it makes field names load-bearing rather than
decorative, and it prevents positional matching on a variant whose author
intended names to be the interface. It is what Rust does.

Rejected because:

- It requires rewriting every struct-variant match arm in tempest, which
  substantially defeats the stated purpose of implementing the feature rather
  than rewriting the calling code.
- It doubles the implementation surface in *both* compilers, and ritz1 is
  significantly behind ritz0 on enums already (§6). Adding a second variant
  kind to a compiler that currently discards payload types entirely is the
  wrong order of operations.
- The strictness it buys can be added later as a lint or an opt-in check
  without changing the representation. Going from sugar to distinct is a
  compatible tightening; going the other way is not.

---

## 3. Memory layout

An enum value is a tag followed by an opaque payload buffer sized for the
largest variant:

```
{ i8 tag, [pad x i8]?, [max_payload x i8] data }
   index 0    index 1        index 1 or 2
```

- **Tag** is always `i8` at struct index 0. The tag value is the variant's
  ordinal in the declaration — first variant is 0.
- **Padding** is present only when the payload needs alignment greater than 1.
  Its width is `(max_align - (1 % max_align)) % max_align`, i.e. enough to push
  the data buffer to `max_align`. When present the data buffer is at index 2,
  otherwise index 1.
- **Data** is `[max_payload x i8]`, where `max_payload` is the maximum over all
  variants of that variant's total field size (§3.1).
- An enum whose variants are all bare lowers to `{ i8 }` with no data buffer.

Payloads are stored inline, by value; enum values are passed and returned by
value.

### 3.1 Field offsets within the payload

Fields are laid out in declaration order, each at the next offset that
satisfies its own alignment:

```
offset = 0
for field in variant.fields:
    offset = align_up(offset, align_of(field))
    place field at offset
    offset += size_of(field)
variant_size = align_up(offset, max_align_of_variant)
```

Interior alignment padding is **required**. A naive running sum
(`offset += size`) places, for example, the `String` in

```ritz
ConsoleLog
    level: i32
    message: String
```

at byte offset 4, where `String` needs 8-byte alignment. The emitter bitcasts
the payload buffer to a typed pointer and loads through it, so LLVM is entitled
to assume natural alignment; a misaligned load there is undefined behaviour,
not merely slow.

Construction and pattern binding compute these offsets with the *same* routine.
Any divergence between the two silently reads a field from the wrong address,
so they must stay in lockstep.

### 3.2 Worked example

```ritz
pub enum Msg
    Stop                     # tag 0, 0 bytes
    Reload(i32)              # tag 1, 4 bytes
    ConsoleLog               # tag 2
        level: i32           #   offset 0, 4 bytes
        message: String      #   offset 8 (aligned up from 4), 24 bytes
```

`max_align` = 8 (String), `max_payload` = 32 (ConsoleLog), so:

```llvm
%enum.Msg = type { i8, [7 x i8], [32 x i8] }   ; 40 bytes
```

`ConsoleLog` is constructed by storing tag `2` at index 0, then `level` at data
offset 0 and `message` at data offset 8.

### 3.3 Payload buffer GEP — a standing trap

The data buffer has LLVM type `[N x i8]*`, a **pointer to an array**. Indexing
a byte within it requires *two* GEP indices:

```llvm
; correct — byte `offset` within the array
getelementptr [N x i8], [N x i8]* %data, i32 0, i32 <offset>

; WRONG — strides by whole [N x i8] arrays; byte offset becomes N*<offset>
getelementptr [N x i8], [N x i8]* %data, i32 <offset>
```

The single-index form was the pre-existing bug that made every variant with
more than one field silently corrupt the stack (see §6). It is offset-0-correct,
so single-field variants — the only kind ritzlib uses — masked it completely.

---

## 4. Pattern matching

A variant pattern binds payload fields to names in the arm body. All three
forms below are accepted; which are available depends on how the variant was
declared.

```ritz
match msg
    # bare variant — no binding
    Stop => stop_loading(renderer)

    # positional binding — available for tuple AND struct variants
    SetViewport(width, height) => set_viewport(renderer, width, height)

    # named binding — struct variants only
    ConsoleLog { level, message } => log(renderer, level, @message)

    # wildcards discard a field without binding it
    Reload(_) => reload(renderer, 0)
```

Rules:

- **Positional patterns** bind by position and are valid for any variant with a
  payload, struct-declared or not. Arity must match the variant's field count.
- **Named patterns** are valid only for struct-declared variants. Each named
  field must exist on the variant. Order does not matter; naming a subset is
  permitted only via an explicit `..` rest pattern (not yet implemented — until
  then, all fields must be named).
- Bindings are introduced by value into the arm's scope and removed at the end
  of the arm.
- A bare `IDENT` pattern that is not a known variant of the scrutinee's enum is
  a catch-all binding, as today.

Qualified forms (`Msg.SetViewport(w, h)`) follow the same rules.

---

## 5. Construction

```ritz
let a = SetViewport(640, 480)                    # positional
let b = SetViewport { width: 640, height: 480 }  # named (struct variants only)
let c = Msg.Stop                                 # bare
```

Named construction reuses the existing struct-literal syntax and is checked the
same way as a named pattern: every field must be present exactly once. Both
forms lower to identical IR.

---

## 6. Compiler status and the ritz0/ritz1 parity gap

The two compilers are **not** at the same level on enums, and this feature is
gated on closing part of that gap.

| Capability | ritz0 | ritz1 |
|---|---|---|
| Bare variants | yes | yes |
| Single-field tuple variants | yes | yes |
| Multi-field tuple variants | parser yes; **emitter miscompiled** (fixed, §3.3) | **cannot parse** |
| Struct variants | this task | this task |
| Payload types retained by parser | yes | **no — discarded** |
| Enum AST node | yes (`EnumDef`/`Variant`) | **none** — a global name side-table |
| Payload sizing | exact, per enum | fixed `[32 x i8]` upper bound |
| Payload load | per-field, typed | always `load i64` at index 1 |
| Match bindings per pattern | N | **exactly 1** (`IDENT LPAREN IDENT RPAREN`) |
| Generic enum specialization | yes | none (name mangling only) |

Three pre-existing defects were found while surveying, all masked by the fact
that no code in the repo had ever used a variant with more than one field:

1. **ritz0 payload GEP** (§3.3) — single-index GEP on `[N x i8]*`. Every field
   after the first was written and read `N × offset` bytes outside the enum.
   Both tests and construction agreed on the wrong address, so values sometimes
   survived while adjacent stack was destroyed. *Fixed.*
2. **ritz0 interior alignment** (§3.1) — offsets were a naive running sum, so a
   field needing 8-byte alignment after an `i32` was misaligned.
3. **ritz1 fixed payload bound** — `TAGGED_ENUM_PAYLOAD_BYTES = 32` is a
   conservative bound chosen when payloads were single scalars. tempest's
   `FetchRequest` (u64 + String + i32 + Vec + Vec = 84 bytes) overflows it.
   ritz1 must compute exact sizes, which requires the parser to stop discarding
   variant payload types.

Because the regression matrix runs every case against ritz0, ritz1 and
ritz1_selfhosted, a struct-variant test cannot be added to the matrix until
ritz1 supports the form. See AGAST #1282 for sequencing.

---

## 7. Related issues

- **#1291** — nested variant patterns bind silently to nothing. Same subsystem
  (match lowering). Not addressed here.
- **#1279** — incremental-cache staleness. `ritz1`'s `.ll` cache keys on source
  content plus a compiler fingerprint; see `docs/STALE_LL_CACHE_TRAP.md`. Any
  emitter change invalidates it, but always confirm with a clean
  `rm -rf ritz1/build` before believing a matrix result.
