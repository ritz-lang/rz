# V1 ABI / Idiom Cleanup

**Status:** Decisions locked in 2026-05-06. Implementation in progress on
worktree `adele-ritz-task-198`.
**Driver:** AGAST `#198` (with phase subtasks).
**Estimated scope:** ~5 days of focused work, hard cutover, single branch.

**Sexiness lens:** every decision below was made through "no syntax for the
common case." `pub fn main()` is the most-written program in any language;
`println("hi")` is the most-written line. Both must be free of ceremony.

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

- Three accepted entry signatures, default zero-ceremony:
  - `pub fn main() -> i32` — most code (the `hello world` shape)
  - `pub fn main(args: Span<StrView>) -> i32` — when args are needed
  - `pub fn main(args: Span<StrView>, env: Span<StrView>) -> i32` — rare
- Optional return type — `pub fn main()` (no `-> i32`) implicitly returns 0
- All argv/envp pre-measured into typed Ritz values; no `**u8` in user space
- Env access via free functions in `ritzlib.os.env` (`env.get`, `env.get_or`,
  `env.iter`) for the 99% case where you look up keys, not iterate them
- Runtime path written in Ritz except for ~10 lines of `_start` asm that's
  forced by the kernel ABI
- Interpolation (`{var}`, `{expr}`, `{x:08x}`) is the **canonical** print API
- Trait-based output: `pub trait Display`, with standard impls in ritzlib and a
  trait-extension hook so user types opt in
- Format specifiers (`x`, `X`, `b`, `o`, width, alignment, `?`) shipped in v1
- `Writer` abstraction so prints can target stdout / stderr / a String / a
  `Span<u8>` / a socket uniformly
- `print` / `println` / `eprint` / `eprintln` implicitly target stdout/stderr;
  `write` / `writeln` / `format` take an explicit writer
- Hard cutover: chained `prints_cstr` / `print_int` style and legacy main
  signatures removed in the same branch — no deprecation window
- All 17 binaries in the workspace migrated; ritzlib code itself migrated

## Non-goals

- Float formatting (separate task — Ritz doesn't have first-class float types yet)
- Locale-aware formatting (out of scope for v1)
- Runtime trait objects / `dyn Display` (static dispatch is enough; user can
  pass a function pointer when needed)
- Replacing the existing logging convention (separate concern from `Display`)

## New entry-point ABI

### Signatures (three accepted; one canonical entry symbol)

```ritz
# Default — the "hello world" shape
pub fn main() -> i32
    println("hello world")
    0

# Implicit return 0 — optional `-> i32` for the common case
pub fn main()
    println("hello world")

# When you need args
pub fn main(args: Span<StrView>) -> i32
    if args.len < 2
        eprintln("usage: {args[0]} <command>")
        return 1
    let cmd: StrView = args[1]
    ...

# When you need env at startup (rare — most code uses env.get(name))
pub fn main(args: Span<StrView>, env: Span<StrView>) -> i32
    for var in env_iter(env)
        println("{var.key}={var.value}")
    0
```

The compiler matches the user's `main` by arity (0, 1, 2) and arg shape
(`Span<StrView>`). All three are emitted under one canonical 2-arg ABI —
`main(args: Span<StrView>, env: Span<StrView>) -> i32` — with unused
parameters silently accepted and discarded. The runtime always calls
`main(args, env)` with no arity branching.

### Overriding the entry symbol

The linker symbol the runtime calls is `main` by default. Any binary may
override this in its `ritz.toml`:

```toml
[[bin]]
name = "kernel"
entry = "kernel_main"     # default: "main"
```

The named function must still match one of the three accepted shapes. This
exists for niche cases (kernel entry points, embedded firmware, custom
runtimes) — application code never needs it. The override only changes
**which `pub fn`** the runtime dispatches to; the canonical 2-arg ABI and
all `Display` / `Writer` machinery are unaffected.

### Env API for the 99% case

Most code looks up keys, doesn't iterate. Free functions in `ritzlib.os.env`
read `/proc/self/environ` lazily on first call:

```ritz
import ritzlib.os.env

# Most common patterns
let port = env.get_or("PORT", "8080")        # StrView
let debug = env.get("DEBUG")                  # Option<StrView>
let home = env.must("HOME")                   # StrView, exits 1 if missing

# Rare path — full iteration
for var in env.iter()
    println("{var.key}={var.value}")
```

This means `pub fn main()` and `pub fn main(args)` programs can still read env;
they just don't have to declare interest in it at the entry point.

### Runtime layering

```
kernel exec()                   ← stack: argc, argv[], NULL, envp[], NULL, auxv...
  ↓
_start (≤10 lines asm)          ← ritzlib/runtime/start.x86_64.ll — forced by kernel ABI
  ↓
fn ritz_start(argc, argv, envp) ← Ritz!  In ritzlib.entry
  ↓
   builds Span<StrView> for argv, envp; calls main(args, env) directly
  ↓
pub fn main(...) -> i32         ← user code, emitted under canonical 2-arg ABI
```

No synthesized adapter symbol — the linker symbol called by `ritz_start` is
literally the user's `pub fn main` (or whatever `[[bin]] entry` names). The
compiler's only job for entry-point dispatch is **emitting** `main` with the
canonical signature regardless of declared arity; no runtime indirection.

The single `_start` is in assembly because the kernel sets up the stack layout
in a way that's not accessible from a normal C-ABI Ritz function call (no
prologue, exec just jumps to `_start` with `argc` at `0(%rsp)`). Above that,
everything is Ritz.

The three existing .ll shims (`ritz_start.x86_64.ll`,
`ritz_start_envp.x86_64.ll`, `ritz_start_noargs.x86_64.ll`) are replaced by one
`ritzlib/runtime/start.x86_64.S` plus `ritzlib/entry/mod.ritz`.

### Compiler enforcement

- The compiler recognizes the three accepted shapes by arity and arg type;
  anything else under the name `main` is a compile error with a friendly
  hint pointing at the canonical signatures.
- `pub fn main` (no return type) is treated as `-> i32`, with `0` returned
  implicitly when the body falls through.
- A program without `pub fn main` (or the configured `[[bin]] entry` symbol)
  is a link error (`error: no public main`).
- `fn main` (without `pub`) is a compile error: `error: main must be declared
  pub` — addresses the consistency issue spotted in rzrz.
- `[[bin]] entry = "<name>"` in `ritz.toml` overrides which `pub fn` the
  runtime dispatches to. Default is `main`. The named function must match
  one of the three accepted shapes.
- **No deprecation window.** Legacy `main(argc: i32, argv: **u8, ...)`
  signatures are rejected in the same branch that lands the new ABI.
  Workspace migration happens in the same commit-set.

### Helpers

```ritz
# ritzlib.entry — argv helpers
pub fn args_program_name(args: Span<StrView>) -> StrView
pub fn args_skip(args: Span<StrView>, n: i32) -> Span<StrView>

# ritzlib.os.env — implicit env access (no Span<StrView> required)
pub fn get(name: StrView) -> Option<StrView>
pub fn get_or(name: StrView, default: StrView) -> StrView
pub fn must(name: StrView) -> StrView   # missing → exits 1 with friendly error
pub fn iter() -> EnvIter

# When the user's main DID take env, they can also pass it explicitly:
pub fn env_get(env: Span<StrView>, name: StrView) -> Option<StrView>
pub fn env_iter(env: Span<StrView>) -> EnvIter
```

`ritzlib.os.env` reads `/proc/self/environ` lazily on first call and caches
the parsed `Span<StrView>`. The compiler ensures even a `pub fn main()`
binary still links the env-reading code path *only* when something in the
program references `ritzlib.os.env` — pay-for-what-you-use.

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

### Format specifiers (in scope for v1)

Current `{x}` becomes `{x[:spec]}`. **Shipped in v1**, scoped to the small
useful set:

| Spec | Use | Example |
|---|---|---|
| `{x:x}` / `{x:X}` | hex (lower/upper) | `{addr:x}` → `7ffe9a3c1234` |
| `{x:08x}` | zero-padded hex of width 8 | `{err:08x}` → `0000002a` |
| `{x:b}` | binary | `{flags:b}` → `1011010` |
| `{x:o}` | octal | `{mode:o}` → `755` |
| `{s:<20}` | left-justified width 20 | `{name:<20}` |
| `{s:>20}` | right-justified width 20 | `{count:>4}` |
| `{s:^20}` | center width 20 | `{title:^40}` |
| `{p:?}` | Debug-trait formatting | `Point { x: 1, y: 2 }` |

Out for v1.1+: float specs (no floats yet), locale, fill-char customization
(`{x:*<8}`), `{:#?}` pretty-print, precision (`.3`).

Lexer parses `:spec` as part of the interp token. Emitter passes `spec` as a
compile-time `StrView` constant to `Display::show_with(self, w, spec)` (a
default-method on `Display` that delegates to `show` when `spec.len == 0`).
Common impls (`i64`, hex, padding) honor it; user types can ignore it.

`{p:?}` resolves to `Debug::show(p, w)` instead of `Display::show`. Both
traits coexist; a type can implement either or both. Default `Debug` for
structs is auto-derived (struct-name + braces + field-name=value pairs) when
no explicit impl is present.

### `print` / `println` / `eprint` / `eprintln` (implicit sinks)

Implicit stdout/stderr — Rust-style. The common case is zero ceremony.

```ritz
# All in ritzlib.fmt — implicit sink, no writer argument
pub fn print(s: StrView)            # → stdout
pub fn println(s: StrView)          # → stdout + newline
pub fn eprint(s: StrView)           # → stderr
pub fn eprintln(s: StrView)         # → stderr + newline

# Explicit writer ONLY when targeting something other than stdout/stderr
pub fn write(w: *Writer, s: StrView) -> i32
pub fn writeln(w: *Writer, s: StrView) -> i32

# Format to a new String (no IO)
pub fn format(s: StrView) -> String
```

Interpolation is a lexer/emitter feature. `println("hello {name}")` lowers at
compile time to a sequence of `write_str` / `Display::show` calls against
stdout's writer. There is no runtime `printf`-style format-string parsing —
the spec is statically known, errors are caught at compile time, and there's
zero allocation in the hot path.

**Rationale for implicit sinks:** Zig's `try stdout.print("...", .{})` is
honest but the verbosity actively hurts readability. Rust's `println!("...")`
is the right shape for the common case — and Ritz's existing API is already
implicit-stdout, so this is the path of least surprise. Custom-writer code
gets `write(@w, "...")`, which is still clean.

## Migration plan — hard cutover, single branch

All phases land in one worktree (`adele-ritz-task-198`), squash-merged or
landed as a small ordered commit-set. **No deprecation window**, no
intermediate-state main. The branch is broken until phase 4 is complete; that
is fine because nobody else is committing to it.

### Phase 1 — runtime + ABI (1.5 days)

1. Add `ritzlib/runtime/start.x86_64.S` (one canonical `_start`, replaces the
   three .ll shims).
2. Add `ritzlib/entry/mod.ritz` with `ritz_start(argc, argv, envp)` that builds
   `Span<StrView>` and calls `main`.
3. Compiler: recognize the three accepted main signatures (arity 0, 1, 2);
   reject anything else; reject non-`pub` main; treat missing return-type as
   `-> i32` with implicit 0.
4. Add `ritzlib.os.env` lazily-loaded environment helpers.
5. Workspace will not link at this phase — that's expected; phase 4 fixes it.

### Phase 2 — Writer + Display + canonical print + format specs (1.5 days)

1. `ritzlib.fmt.writer` (Writer struct + 6 standard sinks).
2. `ritzlib.fmt.display` (Display trait + Debug trait).
3. `ritzlib.fmt.impls` (impls for built-in types).
4. `ritzlib.fmt` re-exports `print` / `println` / `eprint` / `eprintln` /
   `write` / `writeln` / `format`.
5. Format-spec parsing in the lexer; spec passed compile-time-constant to
   `Display::show_with` / `Debug::show_with`.

### Phase 3 — emitter dispatches via trait (0.5 day)

1. Replace `_emit_print_value` hardcoded type-dispatch with trait-method
   resolution + call.
2. Implicit stdout writer for `print` / `println`; implicit stderr for
   `eprint` / `eprintln`; explicit writer arg required for `write` / `writeln`.
3. Compile error message tuned for missing impls: "type X doesn't implement
   Display; add `impl Display for X`".
4. Auto-derive `Debug` for structs when no explicit impl is present.

### Phase 4 — migrate the workspace (1 day mechanical)

1. Convert all 17 binaries' `main()` to the new ABI.
2. Convert ritzlib's chained-print usage to interpolation.
3. Convert nexus / mausoleum / zeus / valet / spire to interpolation.
4. Delete legacy `prints_cstr` / `print_int` / `print_hex` etc. — no
   wrappers, no aliases. The tutorial says one thing, the STYLE.md says one
   thing, the workspace `grep` returns zero hits for the old style.

### Phase 5 — final cleanup (0.25 day)

1. Remove the three .ll shims.
2. Remove any dead code paths the legacy main signatures referenced.
3. Squash-merge the branch onto main (or keep the per-phase commits — call
   it during land).

## Backwards compatibility

**None.** Hard cutover within the worktree. Branch is broken from phase 1
through phase 3; phase 4 brings it back to green; phase 5 polishes. Single
landing onto main.

## Decision log (resolved 2026-05-06)

1. **main ABI shape — RESOLVED: three accepted signatures, one canonical
   entry symbol.** `pub fn main()`, `pub fn main(args: Span<StrView>)`,
   `pub fn main(args: Span<StrView>, env: Span<StrView>)`. All three are
   emitted under the canonical 2-arg ABI `main(args, env) -> i32` with
   unused parameters silently accepted and discarded — the runtime always
   calls `main(args, env)` directly with no synthesized adapter and no
   arity branching. Env access for the 99% case lives in `ritzlib.os.env`
   as free functions (`env.get`, `env.get_or`, `env.must`, `env.iter`).
   Most code never has to declare interest in env at the entry point. The
   entry symbol can be overridden per-binary via `[[bin]] entry = "..."`
   in `ritz.toml`; default is `main`.

2. **`pub fn main` return type — RESOLVED: optional, defaults to `-> i32`
   with implicit 0.** Drives the absolute minimum-syntax `hello world`:
   `pub fn main() { println("hi") }`.

3. **Format specifiers — RESOLVED: in v1 scope.** Small useful set:
   `{x:x}`, `{x:X}`, `{x:08x}`, `{x:b}`, `{x:o}`, `{s:<N}`, `{s:>N}`,
   `{s:^N}`, `{p:?}`. Float specs, locale, fill-char customization,
   pretty-print all v1.1+.

4. **Migration sequence — RESOLVED: hard cutover, single branch.** Ritz is
   pre-v1; backwards-compat exists to protect downstream users; we have none.
   Two ways to write `main` and two ways to print is exactly the kind of
   decay that makes a language feel old at v1.

5. **Print sink — RESOLVED: implicit stdout/stderr.** `print` / `println` →
   stdout, `eprint` / `eprintln` → stderr, `write` / `writeln` / `format`
   take an explicit writer. Rust's path. Zig's `try stdout.print(...)` is
   honest but the verbosity actively hurts readability for the common case.

## Implementation-time questions (decide as we hit them)

1. **`@Self` vs `&Self` syntax in trait declarations.** Existing impl blocks
   use `self: @StrView` (`@` for borrow) and `self: *StrView` (raw pointer).
   The trait sketch uses `@Self`. **Lean:** `@Self` — matches existing impl
   blocks. Decide in Phase 2 when first writing trait declarations.

2. **Generic Display impls** (`impl<T: Display> Display for Span<T>`,
   `Option<T>`, `Result<T,E>`). Ritz1 supports trait bounds on generic
   params; ritz0 needs to as well or we'll have impls available only when
   built with ritz1. **Action:** confirm parity in Phase 2; if ritz0 needs
   work, scope it out of v1 and ship monomorphic impls for the most common
   `Span<T>` substitutions instead.

3. **`fn main` not `pub` is currently silently accepted.** Whether this is
   compiler magic or default linkage — if the latter, fixing the rule has
   wider reach (other "private" functions might also be silently exported).
   **Action:** check the emitter's linkage logic in Phase 1; if scope grows,
   spin off as a separate task.

4. **`Writer` lifetime.** With `state: *u8` carrying a sink-specific pointer,
   we have no lifetime guarantees. **Decision:** ship the unsafe shape now;
   the discipline is "writers are short-lived stack values, sinks outlive
   them"; revisit if real bugs surface.

## Estimate

| Phase | Days |
|---|---|
| 1. Runtime + ABI + env helpers | 1.5 |
| 2. Writer + Display + ritzlib.fmt + format specs | 1.5 |
| 3. Emitter trait dispatch | 0.5 |
| 4. Migrate workspace | 1.0 |
| 5. Final cleanup | 0.25 |
| **Total** | **~4.75 days** |

Single worktree, hard cutover. Each phase becomes an AGAST subtask of #198.

## Out of scope (file as separate AGAST tasks)

- Float formatting (we don't have `f32`/`f64` first-class yet)
- Locale-aware formatting
- `dyn Display` runtime polymorphism
- Replacing the logging convention with a `Logger` trait
- An `args.flag("-h")` parser (separate `Args` library)
- Color/ANSI support in the formatter
