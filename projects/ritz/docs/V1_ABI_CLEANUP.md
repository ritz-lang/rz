# V1 ABI / Idiom Cleanup

**Status:** Phase 1 (runtime + `main` ABI, AGAST #200) landed on main for
ritz0 and ritz1, 2026-11-18. Phase 2 (Writer, Display, format specs, #201)
landed 2026-11-20; see "Phase 2 as built". Phases 3-5 (#202-#204) follow,
one room each, in order. Redone on current main after Aaron's decision of 2026-11-18 (#198:
"Hell yeah, redo that shit. Ritz-ify it.").
**Driver:** AGAST `#198` (with phase subtasks).

> **History.** The 2026-05 attempt (commits 1cc80e6 / 953cfa7) added
> `ritzlib/entry.ritz`, `ritzlib/os/env.ritz` and two `start*.x86_64.ll` shims,
> but no compiler or build path ever used the entry pieces. #3913 deleted them
> on 2026-11-17. They are history, not a base to build on. `ritzlib/os/env.ritz`
> survived and is what Phase 1 uses.

**Sexiness lens:** every decision below was made through "no syntax for the
common case." `pub fn main()` is the most-written program in any language;
`println("hi")` is the most-written line. Both must be free of ceremony.

## The problem

Ritz today has two surfaces that read like *C with different syntax* rather than
something Ritz-native:

1. **Entry-point ABI mirrors C's** (before Phase 1): `fn main(argc: i32, argv: **u8, envp: **u8) -> i32`.
   Three .ll runtime shims per OS (`ritz_start{,_noargs,_envp}`) glued the
   kernel's exec stack to that signature, chosen by `main`'s arity in build.py
   (and by a `main_args` key in ritz.toml for freestanding bins). No Ritz code
   was in the runtime path, and user code had to walk `**u8` and `strlen()` to
   do anything with arguments. A `fn main()` with no return type returned 0
   under ritz0 but was `define void @main` under ritz1, so it exited with
   whatever was left in rax.

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
- One entry path: one `_start` per OS, about 10 lines of asm that the kernel ABI
  forces. Everything above it that builds Ritz values is written in Ritz
- Interpolation (`{var}`, `{expr}`, `{x:08x}`) is the **canonical** print API
- Trait-based output: `pub trait Display`, with standard impls in ritzlib and a
  trait-extension hook so user types opt in
- Format specifiers (`x`, `X`, `b`, `o`, width, alignment, `?`) shipped in v1
- `Writer` abstraction so prints can target stdout / stderr / a String / a
  `Span<u8>` / a socket uniformly
- `print` / `println` / `eprint` / `eprintln` implicitly target stdout/stderr;
  `write` / `writeln` / `format` take an explicit writer
- Legacy C-shaped mains and the chained `prints_cstr` / `print_int` style are
  removed in Phase 5 (#204), once Phase 4 (#203) has migrated the workspace.
  Each phase lands on main green, so in between both forms work. No aliases
  survive #204
- Every binary in the workspace migrated (#203); ritzlib code itself migrated

## Non-goals

- Float formatting (separate task — Ritz doesn't have first-class float types yet)
- Locale-aware formatting (out of scope for v1)
- Runtime trait objects / `dyn Display` (static dispatch is enough; user can
  pass a function pointer when needed)
- Replacing the existing logging convention (separate concern from `Display`)

## New entry-point ABI

### Signatures (as built, Phase 1)

```ritz
# Default — the "hello world" shape; no return type means return 0
pub fn main()
    println("hello world")

# When you need args (args[0] is the program)
pub fn main(args: Span<StrView>) -> i32
    if args.len < 2
        eprintln("usage: {args[0]} <command>")
        return 1
    let cmd: StrView = args[1]
    ...

# When you need env at startup (rare — most code uses env_get(name))
pub fn main(args: Span<StrView>, env: Span<StrView>) -> i32
    for var in env        # each element is "KEY=VALUE"
        println("{var}")
    0
```

`-> i32` is optional on each. `-> void` counts as no return type. The rule is
normative in LANGUAGE_SPEC §5.7. (`println` / `{x}` above are Phase 2-3;
today's examples use `sys_write`, see `examples/tier1_basics/{01_hello,03_echo,11_env}`.)

### One entry path (as built)

There is one `_start` per OS, `runtime/ritz_start.x86_64.ll` and
`runtime/ritz_start.harland.x86_64.ll`. ritz0 embeds the same code when it
compiles a single file without `--no-runtime`. It always calls the C symbol
`main(argc, argv, envp)`. build.py links it for every hosted binary and for
every `link_runtime` freestanding binary. The `main_args` manifest key and the
arity-based shim choice are gone.

- A **C-shaped** `main` (`()`, `(argc: i32, argv: **u8)`,
  `(argc: i32, argv: **u8, envp: **u8)`) returning `i32` *is* that symbol. On
  SysV x86-64 a callee ignores argument registers it doesn't declare, so one
  call site serves all three.
- A **Ritz-native** `main` (one taking `Span<StrView>`), or any `main` with no
  return type, is renamed `__ritz_main`. The compiler adds an adapter written
  in Ritz:

  ```ritz
  pub fn main(argc: i32, argv: **u8, envp: **u8) -> i32
      return __ritz_main(__ritz_args(argc, argv), __ritz_env(envp))
  ```

  (or `__ritz_main(...)` then `0` when the user's main returns nothing). For a
  Span main, three small runtime fns come with it: `__ritz_views`,
  `__ritz_args` and `__ritz_env`. They make one `mmap` for the views, then
  measure each string. A C-shaped program pays nothing.

*Why an adapter, when the 2026-05 plan said "no synthesized adapter"?* That
plan wanted the user's `main` emitted directly with the canonical
`(Span, Span)` LLVM signature, called from a Ritz `ritz_start`. That needs a
by-value aggregate ABI that ritz0 and ritz1 agree on at an extern boundary, and
it needs the runtime to be a separately linked Ritz object on every link path:
build.py, ritz1's Makefile, every pytest harness and ritz0's single-file mode.
That second requirement is exactly what left `entry.ritz` dead. The adapter is
emitted into the user's own module by the same compiler, so it links wherever
`main` does. Its text is identical in both compilers: `ritz0/main_abi.py`, and
`ritz1/src/main_abi.ritz`, with a byte-identity check in
`ritz0/test_main_abi.py`.

### Overriding the entry symbol

`[[bin]] entry` is a build-target key, not a language feature (LARB R68,
#4015; built in #4434). The language has one entry convention: `main`, in
one of §5.7's shapes. The runtime adapter still calls `main`.

A hosted binary's function half must be `main`. A freestanding target may
name the symbol the platform calls (`efi_main`, `kernel_main`); that is the
link entry, and the UEFI link takes it from the manifest. Harland was the
binary that asked. There is no hosted runtime dispatch to some other `pub fn`.

### Env API for the 99% case

Most code looks up keys, doesn't iterate. Free functions in `ritzlib.os.env`
(on main since #3737) read the envp `_start` stored in `__ritz_envp`, falling
back to `/proc/self/environ`, lazily on first call:

```ritz
import ritzlib.os.env

# Most common patterns
let port = env_get_or("PORT", "8080")        # StrView
let debug = env_get("DEBUG")                  # Option<StrView>
# A get-or-die helper is the program's, not the library's (S-ERR-3):
# `match env_get("HOME") { Some(h) => h, None => ... }`

# Rare path — full iteration
for var in env_iter()                         # Span<StrView> of "KEY=VALUE"
    println("{var}")
```

This means `pub fn main()` and `pub fn main(args)` programs can still read env;
they just don't have to declare interest in it at the entry point.

### Runtime layering (as built)

```
kernel exec()                      ← stack: argc, argv[], NULL, envp[], NULL, auxv...
  ↓
_start (~10 lines asm)             ← runtime/ritz_start.<os>.x86_64.ll — forced by kernel ABI
  ↓                                   stores envp in __ritz_envp
main(argc, argv, envp) -> i32      ← C-shaped user main, or the compiler's Ritz adapter
  ↓  (adapter only)                   __ritz_args / __ritz_env build the Span<StrView>s
__ritz_main(args, env)             ← the user's Ritz-native main
```

### Compiler enforcement (as built; ritz0 and ritz1 alike)

- The shape is matched by parameter types (names are free): `()`,
  `(Span<StrView>)`, `(Span<StrView>, Span<StrView>)`, and, until #204, the C
  shapes. Anything else, or a generic, `extern` or `= extern` main, is an
  error at `main`: ``error: `main` must take `()`, `(args: Span<StrView>)` or
  `(args: Span<StrView>, env: Span<StrView>)` ``.
- A return type other than `i32` (or `void`/none) gives
  ``error: `main` must return `i32` or nothing``.
- A Span main without `pub` gives
  ``error: `main` taking `Span<StrView>` must be `pub`: write `pub fn main(...)` ``.
- No return type: `main` returns 0, even when its tail is an i32 expression
  (ritz0 used to return the tail).
- In test mode the file's `main` is dropped (the runner supplies one), so it is
  not checked. An `async fn main` keeps its own synchronous wrapper.
- **Transitional until #204:** C-shaped mains, and `fn main` without `pub` in a
  C shape, are still accepted. Rejecting them now would mean migrating 268
  `.ritz` files and about 700 test sources in the same commit, which is #203's
  job.
- Diagnostics inside an adapted main currently name it `__ritz_main` (#4018).
- `pub` on main has no linkage effect. Both compilers give `main` external
  linkage by name (ritz0 `emitter_llvmlite._declare_function`, ritz1
  `emitter.fn_linkage`), so the old question of whether a non-pub `main` was
  exported by "default linkage" is answered: it is a special case, and it
  widens nothing else.

### Helpers

```ritz
# ritzlib.os.env — implicit env access (no Span<StrView> required)
pub fn env_get(name: StrView) -> Option<StrView>
pub fn env_get_or(name: StrView, default: StrView) -> StrView
pub fn env_iter() -> Span<StrView>          # "KEY=VALUE" each
# get-or-die belongs to the program (S-ERR-3), built on env_get's Option
```

argv helpers (`args_skip`, an `Args` parser) are out of scope (see the end of
this doc). `Span<StrView>` indexing and `.len` cover the common case.

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

## Migration plan — staged on main, one room per phase

The 2026-05 plan was one long-lived branch, broken from Phase 1 to Phase 3.
It is replaced: each phase lands on main by itself, green under ritz0 and
ritz1 (ritz1 parity is the M1.1 rule). Legacy forms keep working until
Phase 5 removes them.

### Phase 1 — runtime + ABI (#200, done; #205 folded in)

1. One `_start` per OS (`runtime/ritz_start{,.harland}.x86_64.ll`, both
   calling `main(argc, argv, envp)`). The `_noargs` / `_envp` shims, build.py's
   arity detection and the `main_args` manifest key were deleted. The Harland
   shim now has the stack 16-byte aligned at the call.
2. ritz0 + ritz1 recognise the accepted shapes, refuse others, require `pub`
   on a Span main and give a main with no return type an implicit 0, through
   the Ritz adapter (`ritz0/main_abi.py`, `ritz1/src/main_abi.ritz`).
3. LANGUAGE_SPEC §5.7 and STDLIB_REFERENCE "Program entry" document it.
   `examples/tier1_basics/01_hello` (`pub fn main()`), `03_echo` (args) and
   `11_env` (env) run it end to end.
4. Tests: `ritz0/test_main_abi.py` (every row on ritz0, ritz1 and
   ritz1_selfhosted).
5. Follow-ups filed here: #4018 (diagnostic names), #4019 (Harland mmap).
   #4020 (`[[bin]] entry`) closed under R68 (#4015) by #4434: a build-target
   key, not a second hosted entry function.

### Phase 2 — Writer + Display + canonical print + format specs (1.5 days)

1. `ritzlib.fmt.writer` (Writer struct + 6 standard sinks).
2. `ritzlib.fmt.display` (Display trait + Debug trait).
3. `ritzlib.fmt.impls` (impls for built-in types).
4. `ritzlib.fmt` re-exports `print` / `println` / `eprint` / `eprintln` /
   `write` / `writeln` / `format`.
5. Format-spec parsing in the lexer; spec passed compile-time-constant to
   `Display::show_with` / `Debug::show_with`.

### Phase 2 as built (#201, 2026-11-20)

The sketches above are the plan; this is what landed. Where they differ, this
wins.

- **Modules.** `ritzlib.fmt` is the one import: it `pub import`s
  `ritzlib.fmt.{digits,spec,writer,impls,display}` and `ritzlib.io`, and
  defines `write`, `writeln` and `format`. The old `ritzlib.fmt` (the integer
  digit routines) is now `ritzlib.fmt.digits`, and every importer moved. It
  had to: `string` imports the digits, `writer` imports `string`, an import
  cycle is an error, and the digits are core (freestanding) while the
  Writer is hosted (`tools/ritzlib_layers.py`).
- **print / eprint are builtins** with interpolation (LANGUAGE_SPEC §2.6,
  #1641, #2102), and `println` / `eprintln` stay in `ritzlib.io`.
  `ritzlib.fmt` adds none of the four; it reaches `println` / `eprintln`
  through `pub import ritzlib.io`.
- **Writer.** `sink: fn(@&Writer, *u8, i64) -> i64`, `state: *u8`, `fd`,
  `cap`, `len`. Lengths are `i64` like the rest of ritzlib, not `i32`. A
  `span_writer` write that doesn't fit is -1 and writes nothing. `len` counts
  bytes accepted, so `null_writer` measures. A Writer has `push_bytes`, so
  it is a `format_into` sink: `format_into(@&w, "x={x}")` works on any sink
  today.
- **Traits.** `Display.show(self: @Self, w: @&Writer) -> i64` and
  `Debug.show_debug(...)`. Debug's method can't also be called `show`:
  methods resolve by name on the concrete type (§12.2), so a type with both
  impls would have two `show`s. Traits have no default methods, so
  `show_with` is not a trait method: `fmt_show_with<T>(v, w, spec)` pads any
  Display type to a spec's width (measuring with a `null_writer`), and the
  integer impls take radix specs themselves. `fmt_show<T>` and
  `fmt_show_debug<T>` are the generic calls.
- **Impls on built-ins are real now.** R36's revisit (#4294) admits
  `impl Display for i64` (and `bool`, `StrView`, `Span<u8>`, `*u8`, the
  integer widths) in the file that declares the trait, so
  `ritzlib.fmt.display` has them, one line each calling the fn.
  `ritzlib.fmt.impls` keeps `fmt_show_T`, `fmt_show_T_with` and `fmt_debug_T`
  for the `_with` spec forms. Phase 3 lowers `{x}` to `show` / `fmt_show<T>`
  by `x`'s type. An inherent impl, an impl outside the trait's file, and
  Option/Result remain refused (§12.2, R36 / R26).
- **Bounds.** The generics are `<T: Display>` (and `<T: Debug>` for
  `fmt_show_debug`): a `T` without the trait is an error at the call, not
  inside the instance (#4295). A bound is a check only (R55).
- **Trait impl methods are reachable.** §15.2 says they need no `pub`; ritz0
  refused a call from a generic in another file and ritz1 gave them internal
  linkage. Both now mark a trait impl's methods `pub` at the parse
  (`ritz0/test_trait_impl_method_reach.py`).
- **Specs.** `ritzlib.fmt.spec`'s `fmt_spec_parse` is the runtime grammar,
  and the compilers lex `{expr:spec}` with the same grammar (see
  LANGUAGE_SPEC §2.6). An unknown spec is a compile error. A valid one is
  refused at the emitter until Phase 3 prints it, so nothing prints a
  placeholder wrongly in between.
- **Tests:** `ritzlib/tests/test_fmt_{writer,impls,display}.ritz` on ritz0,
  ritz1 and ritz1_selfhosted.

### Phase 3 — emitter dispatches via trait (0.5 day)

1. Replace `_emit_print_value` hardcoded type-dispatch with trait-method
   resolution + call.
2. Implicit stdout writer for `print` / `println`; implicit stderr for
   `eprint` / `eprintln`; explicit writer arg required for `write` / `writeln`.
3. Compile error message tuned for missing impls: "type X doesn't implement
   Display; add `impl Display for X`".
4. Auto-derive `Debug` for structs when no explicit impl is present.

### Phase 4 — migrate the workspace (#203)

1. Convert every `main` to a Ritz-native, `pub` shape (268 `.ritz` files and
   about 700 test sources on 2026-11-18).
2. Convert ritzlib's chained-print usage to interpolation.
3. Convert nexus / mausoleum / zeus / valet / spire to interpolation.
4. Delete legacy `prints_cstr` / `print_int` / `print_hex` etc. — no
   wrappers, no aliases.  Done by AGAST #4565: `prints_cstr`,
   `println_cstr`, `print_int`, `print_hex` and `print_string` are gone
   (`tools/test_legacy_printers_deleted.py` keeps them gone). The tutorial says one thing, the STYLE.md says one
   thing, the workspace `grep` returns zero hits for the old style.

### Phase 5 — final cleanup (#204)

1. Refuse the C-shaped mains and any `main` without `pub` (`main_abi.shape`
   'c' → error in both compilers). The adapter then serves every program.
2. Remove any dead code paths the legacy main signatures referenced.

## Backwards compatibility

None is promised; Ritz is pre-v1. Between phases, main stays green and both
forms work. Phase 5 removes the old ones in one commit.

## Decision log (2026-11-18, Phase 1)

6. **Redo on current main — RESOLVED (Aaron, #198).** "Hell yeah, redo that
   shit. Ritz-ify it." Staged phases on main instead of one branch. Open
   questions are settled toward idiomatic Ritz. Language rulings go to LARB
   under #3786 and don't block.
7. **Entry mechanics — RESOLVED: one `_start`, compiler-added Ritz adapter.**
   This replaces the "canonical `(Span, Span)` symbol, no adapter" plan in 1
   below, for the reasons under "One entry path".
8. **Legacy mains — RESOLVED: accepted until #204.** This replaces "no
   deprecation window" in 4 below. A hard cutover on main would be the whole
   of Phase 4 inside Phase 1.

## Decision log (resolved 2026-05-06)

1. **main ABI shape — RESOLVED: three accepted signatures, one canonical
   entry symbol.** `pub fn main()`, `pub fn main(args: Span<StrView>)`,
   `pub fn main(args: Span<StrView>, env: Span<StrView>)`. All three are
   emitted under the canonical 2-arg ABI `main(args, env) -> i32` with
   unused parameters silently accepted and discarded — the runtime always
   calls `main(args, env)` directly with no synthesized adapter and no
   arity branching. Env access for the 99% case lives in `ritzlib.os.env`
   as free functions (`env.get`, `env.get_or`, `env.must`, `env.iter`).
   Most code never has to declare interest in env at the entry point.
   `[[bin]] entry = "..."` was proposed here as a per-binary override of
   the runtime entry symbol. Superseded (R68, #4434): it is a build-target
   key. Hosted binaries name `main`. Freestanding targets name the link
   symbol (`efi_main`, `kernel_main`). The runtime adapter still calls `main`.

2. **`pub fn main` return type — RESOLVED: optional, defaults to `-> i32`
   with implicit 0.** Drives the absolute minimum-syntax `hello world`:
   `pub fn main() { println("hi") }`.

3. **Format specifiers — RESOLVED: in v1 scope.** Small useful set:
   `{x:x}`, `{x:X}`, `{x:08x}`, `{x:b}`, `{x:o}`, `{s:<N}`, `{s:>N}`,
   `{s:^N}`, `{p:?}`. Float specs, locale, fill-char customization,
   pretty-print all v1.1+.

4. **Migration sequence — RESOLVED: hard cutover, single branch** (superseded by 6 and 8 above: staged on main). Ritz is
   pre-v1; backwards-compat exists to protect downstream users; we have none.
   Two ways to write `main` and two ways to print is exactly the kind of
   decay that makes a language feel old at v1.

5. **Print sink — RESOLVED: implicit stdout/stderr.** `print` / `println` →
   stdout, `eprint` / `eprintln` → stderr, `write` / `writeln` / `format`
   take an explicit writer. Rust's path. Zig's `try stdout.print(...)` is
   honest but the verbosity actively hurts readability for the common case.

## Implementation-time questions

1. **`@Self` vs `&Self` syntax in trait declarations.** The lean is `@Self`,
   matching existing impl blocks. **Moved to LARB: #4016.** Phase 2 shipped
   `self: @Self` with `w: @&Writer`, the shape §11.5 and §12 already use.

2. **Generic Display impls** (`impl<T: Display> Display for Span<T>`, …).
   **Moved to LARB: #4017.** Phase 2 shipped no generic impls; bounds parse
   now (#3469). The concrete `impl Display for Span<u8>` and
   `impl Display for i64` (and the like) now exist in `ritzlib.fmt.display`
   (R36's revisit, #4294); `impl<T: Display> ... for Span<T>` still waits on
   #4017.

3. **`fn main` not `pub` is silently accepted.** **RESOLVED (Phase 1):** both
   compilers special-case `main`'s linkage by name, so it widens nothing else.
   `pub` is required on a Span main now and on every main from #204.

4. **`Writer` lifetime.** With `state: *u8` carrying a sink-specific pointer,
   we have no lifetime guarantees. **Decision:** ship the unsafe shape now;
   the discipline is "writers are short-lived stack values, sinks outlive
   them"; revisit if real bugs surface.

## Phases

| Phase | AGAST |
|---|---|
| 1. Runtime + ABI | #200 (done) |
| 2. Writer + Display + ritzlib.fmt + format specs | #201 |
| 3. Emitter trait dispatch | #202 |
| 4. Migrate workspace | #203 |
| 5. Final cleanup | #204 |

## Out of scope (file as separate AGAST tasks)

- Float formatting (we don't have `f32`/`f64` first-class yet)
- Locale-aware formatting
- `dyn Display` runtime polymorphism
- Replacing the logging convention with a `Logger` trait
- An `args.flag("-h")` parser (separate `Args` library)
- Color/ANSI support in the formatter
