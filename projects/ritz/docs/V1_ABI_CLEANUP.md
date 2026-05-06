# V1 ABI / Idiom Cleanup

**Status:** Design doc. Argue with this. Implementation starts when consensus exists.
**Driver:** AGAST task `v1-abi-cleanup` (filed alongside this doc).
**Estimated scope:** 3–5 days of focused work, stageable.

## The problem

Ritz today has two surfaces that read like *C with different syntax* rather than
something Ritz-native:

1. **Entry-point ABI mirrors C's**: `fn main(argc: i32, argv: **u8, envp: **u8) -> i32`.
   Three .ll runtime shims (`ritz_start*.x86_64.ll`) glue the kernel's exec stack
   to that signature. No Ritz code in the runtime path. User code has to walk
   `**u8` and `strlen()` to do anything with arguments.

2. **Output API is a C-shaped function zoo**: `prints_cstr`, `prints`, `print_int`,
   `print_hex`, `print_char`, `print_string`, `println_cstr`, … each typed
   variant gets its own free function. The `{var}` interpolation is implemented
   in the emitter and documented as the preferred style, but **uses hardcoded
   type dispatch** (six branches of `if isinstance(ty, …)` in
   `emitter_llvmlite.py:_emit_print_value`) and **isn't extensible** to user
   types. As a result almost no real code uses interpolation — it's all
   `prints_cstr(c"foo "); print_int(x); prints_cstr(c"\n")` chains.

Both are the same kind of v1 polish: **what does Ritz code look like at the
boundary between the program and the rest of the world?**

## Goals

- Single canonical entry signature: `pub fn main(args: Span<StrView>, env: Span<StrView>) -> i32`
- All argv/envp pre-measured into typed Ritz values; no `**u8` in user space
- Runtime path written in Ritz except for ~10 lines of `_start` asm that's
  forced by the kernel ABI
- Interpolation (`{var}`, `{expr}`, `{x:08x}`) is the **canonical** print API
- Trait-based output: `pub trait Display`, with standard impls in ritzlib and a
  trait-extension hook so user types opt in
- `Writer` abstraction so prints can target stdout / stderr / a String / a
  `Span<u8>` / a socket uniformly
- The chained `prints_cstr` / `print_int` style is removed (or kept as
  one-release deprecated wrappers that call into the trait)
- All 17 binaries in the workspace migrated; ritzlib code itself migrated

## Non-goals

- Float formatting (separate task — Ritz doesn't have first-class float types yet)
- Locale-aware formatting (out of scope for v1)
- Runtime trait objects / `dyn Display` (static dispatch is enough; user can
  pass a function pointer when needed)
- Replacing the existing logging convention (separate concern from `Display`)

## New entry-point ABI

### Signature

```ritz
# ritzlib.entry — single canonical signature
pub fn main(args: Span<StrView>, env: Span<StrView>) -> i32
    if args.len > 0
        println("Program: {args[0]}")
    if args.len < 2
        eprintln("usage: {args[0]} <command> [args...]")
        return 1

    let cmd: StrView = args[1]
    if cmd == "build"
        return cmd_build(args.slice(2))
    ...
```

### Runtime layering

```
kernel exec()                   ← stack: argc, argv[], NULL, envp[], NULL, auxv...
  ↓
_start (≤10 lines asm)          ← ritzlib/runtime/start.x86_64.S — forced by kernel ABI
  ↓
fn ritz_start(argc, argv, envp) ← Ritz!  In ritzlib.entry
  ↓
   builds Span<StrView> for argv, envp; calls user main
  ↓
pub fn main(args, env) -> i32   ← user code
```

The single `_start` is in assembly because the kernel sets up the stack layout
in a way that's not accessible from a normal C-ABI Ritz function call (no
prologue, exec just jumps to `_start` with `argc` at `0(%rsp)`). Above that,
everything is Ritz.

The three existing .ll shims (`ritz_start.x86_64.ll`,
`ritz_start_envp.x86_64.ll`, `ritz_start_noargs.x86_64.ll`) are replaced by one
`ritzlib/runtime/start.x86_64.S` plus `ritzlib/entry/mod.ritz`.

### Compiler enforcement

- The compiler recognizes `pub fn main(args: Span<StrView>, env: Span<StrView>) -> i32`
  as the canonical entry shape.
- A program without `pub fn main` is a link error (`error: no public main`).
- `fn main` (without `pub`) is a compile error: `error: main must be declared
  pub` — addresses the consistency issue you spotted in rzrz.
- The 5 legacy signatures (`()`, `(argc, argv)`, `(argc, argv, envp)`, with and
  without `pub`) are accepted for one release with a deprecation warning, then
  removed. During the deprecation window the compiler synthesizes an adapter
  that calls the legacy main from the new ABI.

### Helpers

```ritz
# ritzlib.entry — argv/envp helpers
pub fn args_program_name(args: Span<StrView>) -> StrView
pub fn args_skip(args: Span<StrView>, n: i32) -> Span<StrView>
pub fn env_get(env: Span<StrView>, name: StrView) -> Option<StrView>
pub fn env_iter(env: Span<StrView>) -> EnvIter   # yields (name, value) pairs
```

## Output: Display, Writer, interpolation

### Core trait

```ritz
# ritzlib.fmt.display
pub trait Display
    fn show(self: @Self, w: *Writer) -> i32
```

`@Self` is a reference (no copy). Returns bytes written or negative on error
(matches the rest of the io API).

### Writer abstraction

```ritz
# ritzlib.fmt.writer
pub struct Writer
    write_fn: fn(*Writer, *u8, i32) -> i32
    state: *u8     # opaque to consumers — sink-specific

pub fn writer_write(w: *Writer, data: *u8, len: i32) -> i32
    return w.write_fn(w, data, len)

# Standard sinks
pub fn stdout_writer() -> Writer       # write(1, ...)
pub fn stderr_writer() -> Writer       # write(2, ...)
pub fn fd_writer(fd: i32) -> Writer
pub fn string_writer(s: *String) -> Writer    # appends to a String
pub fn span_writer(buf: Span<u8>) -> Writer   # bounded; returns -1 on overflow
pub fn null_writer() -> Writer                # /dev/null (for `len(format_str(...))`)
```

The `state` field is `*u8` not generic. We don't have higher-kinded types, and
making `Writer` generic over the sink would require monomorphization for every
sink. The `*u8 + write_fn` pair is fine — it's how every sane vtable works.

### Standard impls

```ritz
# ritzlib.fmt.impls — all in ritzlib

impl Display for i64
impl Display for i32
impl Display for i16
impl Display for i8
impl Display for u64
impl Display for u32
impl Display for u16
impl Display for u8
impl Display for bool
impl Display for StrView
impl Display for String
impl Display for *u8           # null-terminated cstring (current `prints_cstr` semantic)
impl Display for Span<u8>      # raw bytes
# (Span<T> where T: Display, Option<T> where T: Display, Result<T,E> where T,E: Display
#  in a follow-up — needs trait bounds in generics, which ritz1 has but the
#  emitter may need a small change to wire through.)
```

### Interpolation lowering (the only real compiler change)

Today: `_emit_print_value` is a hardcoded `if/elif/elif/else` over LLVM types.

After: the emitter emits a call to `Display::show(value, &writer)` and lets
trait-resolution find the right impl.

```python
# emitter_llvmlite.py:_emit_interp_string_print, after
def _emit_interp_string_print(self, expr):
    writer = self._get_default_writer()  # or threaded through from `print(...)` args
    for i, part in enumerate(expr.parts):
        if part:
            self._emit_writer_write_str(writer, part)
        if i < len(expr.exprs):
            value = self._emit_expr(expr.exprs[i])
            ty = self._ritz_type_of(expr.exprs[i])
            self._emit_trait_method_call("Display", "show", ty, [value, writer])
```

Type without a `Display` impl → compile error: `type Foo doesn't implement
Display; add 'impl Display for Foo'`. No more silent garbage prints.

### Format specifiers (lexer + emitter)

Phase 6 work. Current `{x}` becomes `{x[:spec]}`:

```ritz
println("hex: {x:08x}")           # zero-padded width 8 hex
println("name: {name:<20}")       # left-justified width 20
println("debug: {p:?}")           # uses Debug instead of Display
println("escaped: {s:?}")         # debug-format the string (with quotes/escapes)
```

Lexer parses `:spec` as part of the interp token. Emitter passes `spec` to
`Display::show_with(self, w, spec)` (a default-method on the trait that ignores
the spec unless the impl chooses to honor it). Common impls (i64, hex, padding)
honor it; user types can ignore it.

### `print` / `println` / `eprint` / `eprintln`

Replaced by a single set:

```ritz
# All in ritzlib.fmt
pub fn print(s: StrView)            # always interpolation-aware via emitter
pub fn println(s: StrView)
pub fn eprint(s: StrView)
pub fn eprintln(s: StrView)

# Targeted at a specific writer
pub fn write(w: *Writer, s: StrView) -> i32
pub fn writeln(w: *Writer, s: StrView) -> i32

# Format to a new String (no IO)
pub fn format(s: StrView) -> String
```

The interpolation is purely a lexer/emitter feature; the `print` / `println`
are normal functions that *receive* the already-formatted `StrView`. The magic
happens at compile time: `println("hello {name}")` lowers to a sequence of
`write_str` / `Display::show` calls into stdout's writer.

## Migration plan

### Phase 1 — runtime + ABI (1.5 days)

1. Add `ritzlib/runtime/start.x86_64.S` (one canonical _start, replaces the
   three .ll shims).
2. Add `ritzlib/entry/mod.ritz` with `ritz_start(argc, argv, envp)` that builds
   `Span<StrView>` and calls `main`.
3. Compiler change: when the user's `pub fn main` matches the new shape, link
   the new entry. When it matches a legacy shape, link the new entry **plus** a
   synthesized adapter that converts back to the legacy signature; emit a
   deprecation warning.
4. Compile error for `fn main` (not pub).
5. Build the workspace; expect zero migrations needed at this phase. Old
   binaries link the same as before, just with one new warning.

### Phase 2 — Writer + Display + canonical print (1 day)

1. `ritzlib.fmt.writer` (Writer struct + 6 standard sinks).
2. `ritzlib.fmt.display` (Display trait).
3. `ritzlib.fmt.impls` (impls for built-in types).
4. `ritzlib.fmt` re-exports `print` / `println` / `eprint` / `eprintln` /
   `write` / `writeln` / `format`.
5. Old `prints_cstr` / `print_int` etc. become wrappers that call into the new
   trait — no behavior change at this phase.

### Phase 3 — emitter dispatches via trait (0.5 day)

1. Replace `_emit_print_value` hardcoded type-dispatch with trait-method
   resolution + call.
2. Add the implicit `*Writer` argument: `print("...")` resolves to
   `write(stdout_writer(), "...")` at lowering time.
3. Compile error message tuned for missing impls: "type X doesn't implement
   Display; add `impl Display for X`".

### Phase 4 — migrate the workspace (1 day mechanical)

1. Convert all 17 binaries' `main()` to the new ABI.
2. Convert ritzlib's chained-print usage to interpolation.
3. Convert nexus / mausoleum / zeus / valet / spire to interpolation.
4. Drop deprecated `prints_cstr` / `print_int` wrappers (or keep one release —
   decision below).

### Phase 5 — drop legacy (after one release)

1. Remove the legacy main-signature compiler adapters.
2. Remove the deprecated print wrappers.
3. Remove the .ll shims.

### Phase 6 — format specifiers (optional, 0.5–1 day)

Lexer parses `:spec`; trait gets `show_with(self, w, spec)`; standard impls
honor common specs (`x`, `X`, `o`, `b`, width, alignment, fill).

## Backwards compatibility

| Surface | Phase 1 lands | Phase 4 lands | Phase 5 lands |
|---|---|---|---|
| Old main signatures | accepted, deprecation warning | accepted, deprecation warning | rejected |
| Old print free functions | unchanged | wrappers around trait | removed |
| Old .ll shims | still present, unused | still present, unused | removed |

Workspace stays buildable through phases 1–4. Phase 5 is a clean cutover.

## Open questions

1. **`@Self` vs `&Self` syntax.** Existing impl blocks use `self: @StrView` (`@`
   for borrow) and `self: *StrView` (raw pointer). The trait sketch uses `@Self`.
   Either is fine; need to pick one. I lean `@Self` — matches existing impl
   blocks.

2. **Generic Display impls** (`impl<T: Display> Display for Span<T>`,
   `Option<T>`, `Result<T,E>`). Ritz1 supports trait bounds on generic params;
   ritz0 needs to as well or we'll have impls available only when built with
   ritz1. **Action:** confirm parity before phase 2.

3. **`fn main` not `pub` is currently silently accepted.** Whether this is
   compiler magic or default linkage — if the latter, fixing the rule has wider
   reach (other "private" functions might also be silently exported). **Action:**
   check the emitter's linkage logic before calling this a one-line fix.

4. **`Writer` lifetime.** With `state: *u8` carrying a sink-specific pointer,
   we have no lifetime guarantees. A `string_writer(@my_string)` would be unsafe
   if `my_string` outlives the writer or vice versa. The discipline is "writers
   are short-lived stack values, sinks outlive them" — but should we encode that
   in the type system? **Action:** ship the unsafe shape now; revisit if real
   bugs surface.

5. **Should `print` always implicitly use stdout, or should there be no implicit
   default?** Rust takes the implicit-stdout path; Zig forces you to pass a
   writer. Ritz's existing API is implicit-stdout. **Lean:** keep implicit
   stdout for `print` / `println`; require explicit writer for `write` / `writeln`.

## Estimate

| Phase | Days |
|---|---|
| 1. Runtime + ABI | 1.5 |
| 2. Writer + Display + ritzlib.fmt | 1.0 |
| 3. Emitter dispatch | 0.5 |
| 4. Migrate workspace | 1.0 |
| 5. Drop legacy | 0.25 |
| 6. Format specifiers (optional) | 0.5–1 |
| **Total (1–5)** | **~4.25 days** |
| **Total (1–6)** | **~5.25 days** |

Stageable; phases 1–3 land independently and unlock the rest.

## Decision points

- **Sequence:** land phases 1–4 over 3–4 days, ship to main, run a release on
  it, then phase 5? Or all-at-once cutover?
- **Format specifiers (phase 6):** in scope for the v1 cleanup or follow-up?
- **AGAST decomposition:** one task per phase, or one task with subtasks?
- **Branch strategy:** worktree (`adele-ritz-task-NNN`) or main? This is a
  cross-cutting change — worktree makes more sense than the per-task pattern
  used for #192–#196.

## Out of scope (file as separate AGAST tasks)

- Float formatting (we don't have `f32`/`f64` first-class yet)
- Locale-aware formatting
- `dyn Display` runtime polymorphism
- Replacing the logging convention with a `Logger` trait
- An `args.flag("-h")` parser (separate `Args` library)
- Color/ANSI support in the formatter
