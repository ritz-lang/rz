# Write Ritz, not C

`c"strings"` are only for C interop, where you can't pass a length and the
callee needs NUL termination. Their use is heavily discouraged wherever a safer
API exists: null termination is unsafe. A `c""` (or any NUL-terminated `*u8`
text) belongs only at a boundary that requires it, such as a syscall's
path/argv argument or an `extern fn`, ideally inside a ritzlib wrapper. App code
passes `StrView`/`String`. If the only API for something takes NUL-terminated
`*u8`, the fix is a `StrView` API in ritzlib, not a `c""` at the call site.

Rules: [`STANDARD.md`](STANDARD.md). Review: [`REVIEW.md`](REVIEW.md). Reference:
[`LANGUAGE_SPEC.md`](LANGUAGE_SPEC.md). `make check-doc-examples` compiles every block here.

| # | C habit | Ritz form | Rule |
|---|---|---|---|
| 1 | `c"..."`, NUL-terminated `*u8` text | `"..."` is a `StrView`; `c""` only at the interop boundary | S-TEXT-1 |
| 2 | `*u8` + length | `StrView` for text, `Span<T>` (`[T]`) for elements | S-PTR-2 |
| 3 | `*_cstr`, `strcmp`, `strlen` | `StrView` methods: `.eq`, `.cmp`, `.len`, `.starts_with` | S-TEXT-1 |
| 4 | `i32` status, `return -1` | `Result<T, E>` with a named error enum | S-RESULT-1, S-RESULT-2 |
| 5 | out-parameter beside a status | return the value (a struct, `Option` or `Result`) | S-RESULT-3 |
| 6 | `null` for "nothing" | `Option<T>` | S-OPTION-1 |
| 7 | `malloc` / `free` | an owning type (`String`, `Vec`, `Box`, your `Drop` type) | S-OWN-1..3 |
| 8 | `goto cleanup` | `defer` right after the acquire | S-OWN-4 |
| 9 | an integer as a bool | `bool`; test integers with `n != 0` | S-BOOL-1..3 |
| 10 | a raw `sys_*` call in app code | the ritzlib wrapper (`fs`, `fd`, `process`, `time`) | S-RESULT-2, S-PTR-1 |

Rows 1-3: text is a `StrView`.

```ritz
import ritzlib.io
import ritzlib.strview

fn is_flag(arg: StrView) -> bool              # 3: not strncmp(arg, "--", 2)
    arg.starts_with("--") and arg.len() > 2

fn count_byte(s: StrView, b: u8) -> i64       # 2: not (p: *u8, n: i64)
    var n: i64 = 0
    for i in 0..s.len
        if s.get(i) == b
            n += 1
    n

fn main() -> i32
    prints("hello\n")                         # 1: not prints_cstr(c"hello\n")
    if is_flag("--verbose") and "a".eq("a")   # 3: not strcmp(a, b) == 0
        return count_byte("a,b", ',') as i32
    0
```

Rows 4-6, 9-10: `Result`, `Option`, return values, `bool`, ritzlib wrappers.

```ritz
import ritzlib.errno
import ritzlib.fs
import ritzlib.option
import ritzlib.result

enum PortError
    Empty
    TooBig

fn parse_port(s: StrView) -> Result<i64, PortError>   # 4, 5: not -1 + an out-param
    match s.parse_i64()
        Some(n) => if n > 65535 then Err(PortError.TooBig) else Ok(n)
        None => Err(PortError.Empty)

fn first_comma(s: StrView) -> Option<i64>            # 6: not null / -1
    let i = s.find_byte(',')
    if i < 0 then None else Some(i)

fn config_size(path: StrView) -> Result<i64, Errno>  # 10: not sys_stat(c"...")
    file_size(path)

fn has_config() -> bool                             # 9: not an i32 0/1
    path_exists("/etc/ritz.toml")
```

Rows 7-8: an owning type frees itself; anything else is a `defer`.

```ritz
import ritzlib.memory
import ritzlib.string

fn greeting_len() -> i64                    # 7: not malloc + strcpy + free
    var s = string_from("hello")
    s.push_str(", world")
    s.len()                                 # freed once, at the end of the fn

fn scratch(size: i64, fail: bool) -> i64    # 8: not goto cleanup
    var arena = arena_new(size)
    defer arena.destroy()
    if fail
        return 0
    arena.used()
```
