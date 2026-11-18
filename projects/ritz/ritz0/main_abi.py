"""The program entry ABI (docs/V1_ABI_CLEANUP.md, AGAST #200).

There is one entry path. The runtime's only `_start`
(`runtime/ritz_start*.ll`, or the one ritz0 embeds) calls the C symbol
`main(argc, argv, envp)`. A `main` written in that C shape, `()`,
`(argc: i32, argv: **u8)` or `(argc, argv, envp)`, returning `i32`, *is* that
symbol, as before.

The Ritz-native shapes are

    pub fn main()
    pub fn main(args: Span<StrView>)
    pub fn main(args: Span<StrView>, env: Span<StrView>)

each with or without `-> i32`. Where `-> i32` is left off, main returns 0.
For these shapes the user's fn becomes `__ritz_main`, and this pass adds
an adapter `main(argc, argv, envp) -> i32`, written in Ritz (`adapter_source`),
that builds the spans and calls it. A `main` with no return type takes
the adapter even with no params, so it returns 0 under both compilers (ritz1
used to emit `void @main` and exit with whatever was in rax).

ritz1 does the same in ritz1/src/main_abi.ritz. Messages and the adapter
text are identical in both; test_main_abi.py holds them to that.

`main` must not be generic, `extern` or a declaration. Any other parameter
list or return type is refused (`check_main`). A `Span<StrView>` main must be
`pub`. A legacy C-shaped main without `pub` is still accepted until the
workspace migration (#203) and the cleanup (#204).
"""
from typing import List, Optional

import ritz_ast as rast

ADAPTED_NAME = "__ritz_main"

MSG_SHAPE = ("`main` must take `()`, `(args: Span<StrView>)` or "
             "`(args: Span<StrView>, env: Span<StrView>)`")
MSG_RET = "`main` must return `i32` or nothing"
MSG_PUB = "`main` taking `Span<StrView>` must be `pub`: write `pub fn main(...)`"

# The runtime half of the entry path, in Ritz: one `mmap` for the views,
# then a `strlen` per string. Added only for a Span main, so a C-shaped
# program pays nothing. SYS_mmap is 9, PROT_READ|PROT_WRITE is 3,
# MAP_PRIVATE|MAP_ANONYMOUS is 0x22. The mmap is Linux's (Harland: #200
# follow-up).
RUNTIME_SOURCE = """\
fn __ritz_views(n: i64, p: **u8) -> Span<StrView>
    var r: i64 = 9
    var addr: i64 = 0
    var size: i64 = n * 16 + 16
    var prot: i64 = 3
    var flags: i64 = 34
    var fd: i64 = -1
    var off: i64 = 0
    asm x86_64 (inout r: rax, in addr: rdi, in size: rsi, in prot: rdx, in flags: r10, in fd: r8, in off: r9, clobber rcx, clobber r11):
        syscall
    var out: Span<StrView>
    out.ptr = null
    out.len = 0
    if r < 0
        return out
    let views: *StrView = r as *StrView
    var i: i64 = 0
    while i < n
        let s: *u8 = p[i]
        var k: i64 = 0
        while s[k] != 0
            k = k + 1
        views[i].ptr = s
        views[i].len = k
        i = i + 1
    out.ptr = views
    out.len = n
    out

fn __ritz_args(argc: i32, argv: **u8) -> Span<StrView>
    __ritz_views(argc as i64, argv)

fn __ritz_env(envp: **u8) -> Span<StrView>
    var n: i64 = 0
    if envp != null
        while envp[n] != null
            n = n + 1
    __ritz_views(n, envp)
"""


def _is_named(ty: rast.Type, name: str) -> bool:
    return isinstance(ty, rast.NamedType) and ty.name == name and not ty.args


def _is_span_strview(ty: rast.Type) -> bool:
    return (isinstance(ty, rast.NamedType) and ty.name == "Span"
            and len(ty.args) == 1 and _is_named(ty.args[0], "StrView"))


def _is_ptr_ptr_u8(ty: rast.Type) -> bool:
    return (isinstance(ty, rast.PtrType) and isinstance(ty.inner, rast.PtrType)
            and _is_named(ty.inner.inner, "u8"))


def returns_value(fn: rast.FnDef) -> bool:
    """`-> void` is no return type, as ritz1 parses it and as the emitter's
    `_is_procedure` already reads it."""
    return fn.ret_type is not None and not _is_named(fn.ret_type, "void")


def shape(fn: rast.FnDef) -> Optional[str]:
    """'c' for a C-shaped param list, 'span' for a Ritz-native one, None if
    neither."""
    types = [p.type for p in fn.params]
    if not types:
        return "c"
    if all(_is_span_strview(t) for t in types) and len(types) <= 2:
        return "span"
    if (len(types) in (2, 3) and _is_named(types[0], "i32")
            and all(_is_ptr_ptr_u8(t) for t in types[1:])):
        return "c"
    return None


def find_main(module: rast.Module) -> Optional[rast.FnDef]:
    for item in module.items:
        if isinstance(item, rast.FnDef) and item.name == "main":
            return item
    return None


def check_main(fn: rast.FnDef) -> List[str]:
    """The entry-ABI errors for this `main`, `file:line:col: error: ...`."""
    sp = fn.span
    where = f"{sp.file}:{sp.line}:{sp.column}: error: "
    kind = shape(fn)
    if kind is None or fn.type_params or fn.is_extern or fn.is_decl:
        return [where + MSG_SHAPE]
    if returns_value(fn) and not _is_named(fn.ret_type, "i32"):
        return [where + MSG_RET]
    if kind == "span" and not fn.is_pub:
        return [where + MSG_PUB]
    return []


def needs_adapter(fn: rast.FnDef) -> bool:
    return shape(fn) == "span" or not returns_value(fn)


SPAN_ARGS = ("__ritz_args(argc, argv)", "__ritz_env(envp)")
C_ARGS = ("argc", "argv", "envp")


def adapter_source(fn: rast.FnDef) -> str:
    """The `main` the C entry calls: it calls `__ritz_main` (the user's
    main) with what it takes, and returns its i32, or 0 if it returns
    nothing."""
    pool = SPAN_ARGS if shape(fn) == "span" else C_ARGS
    args = pool[:len(fn.params)]
    returns = returns_value(fn)
    call = f"{ADAPTED_NAME}({', '.join(args)})"
    body = f"    return {call}\n" if returns else f"    {call}\n    0\n"
    return "pub fn main(argc: i32, argv: **u8, envp: **u8) -> i32\n" + body


def lower_main(module: rast.Module, source_path: str) -> List[str]:
    """Check this file's `main`. If it needs the adapter, rename it and add
    the adapter (plus the span runtime for a Span main) to `module`. Returns
    the errors; the module is unchanged when there are any.

    An `async fn main` is left alone: the emitter gives it its own
    synchronous wrapper."""
    fn = find_main(module)
    if fn is None or fn.is_async:
        return []
    errors = check_main(fn)
    if errors or not needs_adapter(fn):
        return errors
    from module_interface import parse_source_tokens
    text = adapter_source(fn)
    if shape(fn) == "span" and fn.params:
        text += "\n" + RUNTIME_SOURCE
    _, generated = parse_source_tokens(text, source_path)
    fn.name = ADAPTED_NAME
    module.items.extend(generated.items)
    return []
