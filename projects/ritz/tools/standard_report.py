#!/usr/bin/env python3
"""Count violations of docs/STANDARD.md's idiom rules (AGAST #1344).

The idiom rules in docs/STANDARD.md Part I (bool for truth values, Result
for failure, Option for absence, references and spans for parameters, impl
blocks for behaviour, ownership, aborting) are ADVISORY: no compiler refuses
a violation yet.  Each one names a *counting rule* here, so the question
"how many violations does ritzlib have?" has an answer you can re-run rather
than argue about.  #1347 converts ritzlib against these counts.

This is a report, not a gate: it always exits 0.  A rule that a tool refuses
is marked ENFORCED in the standard, and this script is not that tool.

Usage:
    python3 tools/standard_report.py [PATH ...]          # default: ritzlib
    python3 tools/standard_report.py --list KEY [PATH ...]
    python3 tools/standard_report.py --json [PATH ...]
    python3 tools/standard_report.py --callers [--json] [--lib LIB] [PATH ...]
    python3 tools/standard_report.py --c-literals [--json] [PATH ...]

THE COUNTING RULES (each is the "Report:" line of a rule in STANDARD.md)
-----------------------------------------------------------------------

"API fn" means a ``pub fn`` at module level, or any fn in an inherent
``impl Type`` block.  Fns in a trait impl (``impl Drop for T``) are skipped
for the signature rules, because the trait fixes their signature.  Test
directories (``tests/``, ``test/``) and ``[[test]]`` / ``[[test_helper]]``
fns are never counted.

  bool-return      API fn with an integer return whose name is a predicate:
                   a ``_``-separated word in PREDICATE_WORDS, a name
                   ending in ``eq`` (``streq``, ``memeq``), or a C ctype
                   name matching ``^is[a-z]+$`` (``isdigit``).
  sentinel-return  API fn with an integer return whose body has
                   ``return -<digit>``.
  status-return    API fn with an integer return whose body has
                   ``return -IDENT`` (a named code such as ``-EINVAL``,
                   or ``Err(e) => return -e.code()``), passes a syscall's
                   raw result straight through (``return syscallN(`` /
                   ``return sys_*(``), passes a callee's negative back up
                   (``if r < 0`` / ``return r``), gives a negative literal
                   as a tail or arm (``Err(_) => -1``), or only ever
                   returns ``0`` (it should return ``()``) (#4929).
  out-param        each non-self parameter that carries a result back
                   through itself: a ``:&`` / ``@&`` / ``*`` parameter
                   whose pointee is a scalar, ``StrView``, ``String`` or
                   a pointer (``*u8``/``*i8`` byte buffers excepted), and
                   that the body assigns (``p = ``, ``*p = ``, ``p.f = ``,
                   ``p[i] = ``, ``*(p + k) = ``, compound ``+=`` ...) or,
                   unless the pointee is itself a pointer (an argv array),
                   hands to a ``sys_*(`` / ``syscallN(`` call.
  null-return      API fn returning ``*T``/``@T``/``@&T`` whose body has
                   ``return null``.
  raw-ptr-param    each ``*T`` parameter of an API fn, and each ``*T``
                   parameter of a fn-type parameter (``handler: fn(*Task)
                   -> i32``): a raw pointer in a callback type makes every
                   callback take one (#4929).
  ptr-len-param    API fn with a ``*T`` parameter followed directly by an
                   integer parameter named in LENGTH_NAMES or ending in
                   ``_len``.
  free-fn-method   a public module-level fn whose first parameter's type,
                   with references, pointers and generics stripped, is a
                   struct or enum declared in the same file.
  raw-receiver     a ``pub`` method of an inherent impl whose ``self`` is a
                   raw pointer (``self: *T``, ``self: **T``).
  ptr-return       an API fn whose return type is, or wraps, a raw ``*T``
                   (``-> *T``, ``Option<*T>``, ``Result<*T, E>``).
  raw-alloc        each call to an ALLOC_FNS function, except in a method,
                   or in a fn whose first parameter or return type is a
                   struct declared in the same file (the owning type's own
                   constructor, growth and release functions).
  lib-exit         each ``sys_exit(`` call outside ``main``.

EXEMPTIONS
----------

An exception is written next to the code it excuses, with a reason:

    # standard-exempt: raw-ptr-param, ptr-len-param: the write(2) ABI
    pub fn sys_write(fd: i32, buf: *u8, n: i64) -> i64

The comment must be in the comment/attribute block directly above the fn.
For a whole module, put this in the file's leading comment block:

    # standard-exempt-file: raw-alloc: this module is the allocator

A file exemption may be scoped to the fns whose names match a glob, so a
module's kernel-ABI layer is excused without excusing the rest of it:

    # standard-exempt-file(sys_*): status-return: the kernel returns -errno

A reason under MIN_REASON characters, or a key that isn't a counting rule,
is itself counted, as ``exempt-malformed``.  Exempt sites are still listed
and counted, in their own column, so exemptions can't pile up unseen.

CALLERS (#4636)
---------------

An exemption says a raw boundary is raw by nature; it doesn't say the rest
of the tree should use it.  ``--callers`` counts how far the raw layer
escapes: for each *exempt API* (a ``pub`` module-level fn of the library
with at least one exempt site), every call ``name(`` in the given trees,
outside the library's sources (its ``tests/`` counts, AGAST #4928), in a file that imports the defining module
(``import ritzlib.<mod>``, and when the import lists names, lists this
one).  A method call ``x.name(`` is not a call of the free fn.  Totals are
grouped by project (the first directory under each PATH; default:
``projects/``).

C LITERALS (#4673)
------------------

``--c-literals`` counts ``c"..."`` literals in every .ritz file under the
given trees (tests included; build output and hidden dirs not), grouped by
project like ``--callers``.  STANDARD.md S-TEXT-1: a NUL-terminated literal
belongs only at a C-interop boundary, so the count only goes down
(tools/test_standard_callers.py pins it per project).  A ``c`` counts as the
prefix only when it directly precedes a literal's opening quote and isn't
the tail of a longer identifier; quotes inside a literal, a char literal or
a ``#`` comment are not literals.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# key -> (rule ID in docs/STANDARD.md, one-line description)
RULES: dict[str, tuple[str, str]] = {
    "bool-return": ("S-BOOL-2", "predicate returns an integer, not bool"),
    "sentinel-return": ("S-RESULT-1", "failure signalled by a negative integer return"),
    "status-return": ("S-RESULT-2", "bare integer status: named -code or raw syscall result"),
    "out-param": ("S-RESULT-3", "result written through a parameter"),
    "null-return": ("S-OPTION-1", "absence signalled by returning null"),
    "raw-ptr-param": ("S-PTR-1", "raw *T parameter on an API fn"),
    "ptr-len-param": ("S-PTR-2", "(*T, length) pair instead of Span<T>/StrView"),
    "free-fn-method": ("S-IMPL-1", "free fn on a type this module declares"),
    "raw-receiver": ("S-IMPL-3", "method takes a raw *T self, not @T / @&T"),
    "ptr-return": ("S-PTR-7", "raw *T returned: a borrow or a view instead"),
    "raw-alloc": ("S-OWN-2", "raw allocation outside the owning type"),
    "lib-exit": ("S-ERR-3", "library code ends the program"),
}
MALFORMED = "exempt-malformed"
MIN_REASON = 12

INT_TYPES = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "isize", "usize"}
# A pointee an out-param writes back: a scalar, a text handle or a pointer.
OUT_SCALARS = INT_TYPES | {"bool", "f32", "f64"}
OUT_HANDLES = {"StrView", "String"}
BYTE_TYPES = {"u8", "i8"}  # `*u8` is a byte buffer: S-PTR-1/S-PTR-2 count it
PREDICATE_WORDS = {
    "is", "has", "can", "contains", "exists", "eq", "equals", "starts", "ends",
    "valid", "empty", "matches",
}
LENGTH_NAMES = {"len", "n", "size", "count", "cap", "nbytes", "length"}
ALLOC_FNS = ("malloc", "free", "realloc", "calloc", "heap_alloc", "heap_free",
             "heap_realloc", "sys_mmap", "sys_munmap", "mmap", "munmap")

# A raw `*T` at the start of a return type or just inside a generic's `<` / `,`.
RAW_RET_RE = re.compile(r"(?:^|[<,])\s*\*")
ALLOC_RE = re.compile(r"(?<![\w.])(" + "|".join(ALLOC_FNS) + r")\s*\(")
EXIT_RE = re.compile(r"(?<![\w.])sys_exit\s*\(")
NEG_RETURN_RE = re.compile(r"^\s*return\s+-\s*\d")
# `return -EINVAL`, also as a match arm: `Err(e) => return -e.code()` (#4929).
NAMED_NEG_RETURN_RE = re.compile(r"^\s*(?:.*=>\s*)?return\s+-\s*[A-Za-z_]")
# A trailing negative literal with no `return`: a tail or an arm, `Err(_) => -1`.
NEG_TAIL_RE = re.compile(r"^\s*(?:.*=>\s*)?-\s*\d+\s*$")
# `if ret < 0`: a callee's result tested for a negative status.
NEG_TEST_RE = re.compile(r"^\s*(?:if|elif)\s+(\w+)\s*<\s*0\s*$")
RETURN_RE = re.compile(r"^\s*(?:.*=>\s*)?return\b\s*(.*?)\s*$")
SYSCALL_CALL = r"(?<![\w.])(?:sys_\w+|syscall\d)\s*\("
PASSTHROUGH_RE = re.compile(r"^\s*return\s+" + SYSCALL_CALL)
SYSCALL_RE = re.compile(SYSCALL_CALL)
# The assignment operator of a statement: `=` or a compound `op=`, never
# `==`, `!=`, `<=`, `>=` or `=>`.
ASSIGN_OP_RE = re.compile(r"(?:<<|>>|[-+*/%|&^])?(?<![=!<>])=(?![=>])")
CTYPE_PRED_RE = re.compile(r"^is[a-z]+$")
NULL_RETURN_RE = re.compile(r"^\s*return\s+null\b")
FN_RE = re.compile(r"^(\s*)(pub\s+)?(?:async\s+)?fn\s+(\w+)")
TYPE_DECL_RE = re.compile(r"^(?:pub\s+)?(struct|enum)\s+(\w+)")
IMPL_RE = re.compile(r"^(\s*)impl\b(?:<[^>]*>)?\s*(.*)$")
EXEMPT_RE = re.compile(r"^\s*#\s*standard-exempt:\s*(.*)$")
EXEMPT_FILE_RE = re.compile(r"^\s*#\s*standard-exempt-file(?:\(([\w*?]+)\))?:\s*(.*)$")
TEST_ATTR_RE = re.compile(r"^\s*\[\[\s*test(_helper)?\s*\]\]")
TEST_DIRS = {"tests", "test"}


@dataclass(frozen=True)
class Site:
    key: str
    path: str
    line: int
    fn: str
    detail: str
    exempt: str | None  # the reason, when exempt


def strip_comment(line: str) -> str:
    """`line` without a trailing `#` comment and with string/char literals blanked."""
    out = []
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
                out.append(ch)
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def split_top(text: str, sep: str = ",") -> list[str]:
    """Split on `sep` outside <>, (), []."""
    parts, depth, cur = [], 0, []
    for ch in text:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return [p.strip() for p in parts]


def param_mode(param: str) -> str:
    """The modifier of one parameter: `&` for `a:& T`, `=` for `a:= T`, else ``""``."""
    m = re.match(r"\w+\s*:\s*([&=])", param.strip())
    return m.group(1) if m else ""


def param_type(param: str) -> tuple[str, str]:
    """(name, type) of one parameter: `a: T`, `a:& T`, `a:= T`, `self`, `self:&`."""
    m = re.match(r"(\w+)\s*(?::\s*[&=]?\s*(.*))?$", param.strip())
    if not m:
        return "", param.strip()
    return m.group(1), (m.group(2) or "").strip()


def base_type(ty: str) -> str:
    """`@&Vec<T>` / `*Box<T>` / `**C` -> `Vec` / `Box` / `C`."""
    ty = ty.strip()
    while ty[:1] in ("@", "*", "&"):
        ty = ty[1:].lstrip()
    return re.split(r"[<\[\s]", ty, maxsplit=1)[0]


def is_predicate(name: str) -> bool:
    words = name.split("_")
    return (bool(PREDICATE_WORDS.intersection(words)) or name.endswith("eq")
            or bool(CTYPE_PRED_RE.match(name)))


def out_pointee(ty: str, mode: str) -> str | None:
    """The type an out-param writes back through, or None if `ty` can't be one."""
    ty = ty.strip()
    if mode == "&":
        return ty
    if ty.startswith("@&"):
        return ty[2:].strip()
    if ty.startswith("*"):
        pointee = ty[1:].strip()
        return None if pointee in BYTE_TYPES else pointee
    return None


def writes_back(pointee: str) -> bool:
    return (pointee in OUT_SCALARS or base_type(pointee) in OUT_HANDLES
            or pointee[:1] in ("*", "@"))


def assigns(code: str, name: str) -> bool:
    """`code` is a statement assigning through `name`: `name = `, `*name = `,
    `name.f = `, `name[i] = `, `*(name + k) = ` or a compound `op=`."""
    m = ASSIGN_OP_RE.search(code)
    if not m:
        return False
    lhs = code[:m.start()].strip()
    if re.match(r"(let|var|if|while|elif|return)\b", lhs):
        return False
    return bool(re.match(r"\*?\s*\(?\s*" + re.escape(name) + r"\b", lhs))


def hands_to_syscall(code: str, name: str) -> bool:
    m = SYSCALL_RE.search(code)
    return bool(m) and re.search(r"\b" + re.escape(name) + r"\b", code[m.end():]) is not None


def passes_negative_up(body: list[tuple[int, str]]) -> bool:
    """`body` tests a value for `< 0` and returns that value: `if r < 0` /
    `return r`, a callee's negative status handed back to the caller."""
    tested = {m.group(1) for _, c in body if (m := NEG_TEST_RE.match(c))}
    return any((m := RETURN_RE.match(c)) and m.group(1) in tested for _, c in body)


def only_returns_zero(body: list[tuple[int, str]]) -> bool:
    """Every value `body` can give is `0`: each `return` is `return 0`, and the
    tail (the last line at the body's own indent) is `0` or `return 0`.  Such
    an integer return carries no information; the fn should return ()."""
    if not body:
        return False
    base = min(len(c) - len(c.lstrip()) for _, c in body)
    tail = body[-1][1]
    if len(tail) - len(tail.lstrip()) != base or tail.strip() not in ("0", "return 0"):
        return False
    return all(m.group(1) == "0" for _, c in body if (m := RETURN_RE.match(c)))


def is_status(body: list[tuple[int, str]]) -> bool:
    """`body`'s integer return is a status code (S-RESULT-2)."""
    return (any(NAMED_NEG_RETURN_RE.match(c) or PASSTHROUGH_RE.match(c) or NEG_TAIL_RE.match(c)
                for _, c in body)
            or passes_negative_up(body) or only_returns_zero(body))


def fn_type_raw_params(ty: str) -> list[str]:
    """The raw `*T` parameters of a fn type `fn(*Task, i32) -> i32` (#4929)."""
    ty = ty.strip()
    if not re.match(r"fn\s*\(", ty):
        return []
    # The parameter list ends at the `)` that balances the `fn(`.
    inner = ty[ty.find("(") + 1:]
    depth, end = 0, len(inner)
    for k, ch in enumerate(inner):
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            if depth == 0:
                end = k
                break
            depth -= 1
    return [p for p in split_top(inner[:end]) if p.startswith("*")]


def parse_exemption(spec: str) -> tuple[set[str], str | None]:
    """`key[, key]: reason` -> (keys, reason). reason None means malformed."""
    if ":" not in spec:
        return set(), None
    key_part, reason = spec.split(":", 1)
    ks = {k.strip() for k in key_part.split(",") if k.strip()}
    reason = reason.strip()
    if not ks or not ks.issubset(RULES) or len(reason) < MIN_REASON:
        return ks, None
    return ks, reason


@dataclass
class Fn:
    name: str
    line: int          # 1-based line of `fn`
    indent: int
    public: bool
    in_impl: str | None   # None, "inherent" or "trait"
    params: list[tuple[str, str]]
    ret: str
    body: list[tuple[int, str]]  # (line, code without comments)
    is_test: bool
    exemptions: list[tuple[set[str], str | None]]
    modes: list[str] | None = None  # param_mode of each parameter


def _leading_block(lines: list[str], idx: int) -> list[str]:
    """The contiguous comment/attribute lines directly above lines[idx]."""
    out = []
    j = idx - 1
    while j >= 0:
        s = lines[j].strip()
        if s.startswith("#") or s.startswith("[["):
            out.append(lines[j])
            j -= 1
        else:
            break
    return out


def parse_fns(text: str) -> tuple[list[Fn], set[str], list[tuple[set[str], str | None, str | None]]]:
    """(fns, declared type names, file exemptions as (keys, reason, name glob))."""
    lines = text.split("\n")
    types = {m.group(2) for ln in lines if (m := TYPE_DECL_RE.match(ln))}
    file_exempt = []
    for ln in lines:
        s = ln.strip()
        if s and not s.startswith("#"):
            break
        if m := EXEMPT_FILE_RE.match(ln):
            file_exempt.append((*parse_exemption(m.group(2)), m.group(1)))

    fns: list[Fn] = []
    impl_stack: list[tuple[int, str]] = []  # (indent, kind)
    i = 0
    while i < len(lines):
        raw = lines[i]
        code = strip_comment(raw)
        if not code.strip():
            i += 1
            continue
        indent = len(code) - len(code.lstrip())
        while impl_stack and indent <= impl_stack[-1][0]:
            impl_stack.pop()
        if m := IMPL_RE.match(code):
            kind = "trait" if re.search(r"\bfor\b", m.group(2)) else "inherent"
            impl_stack.append((indent, kind))
            i += 1
            continue
        m = FN_RE.match(code)
        if not m:
            i += 1
            continue
        start = i
        # Join the signature until its parentheses balance.
        sig = code
        while sig.count("(") > sig.count(")") and i + 1 < len(lines):
            i += 1
            sig += " " + strip_comment(lines[i]).strip()
        open_at = sig.find("(")
        depth, close_at = 0, -1
        for k in range(open_at, len(sig)):
            if sig[k] == "(":
                depth += 1
            elif sig[k] == ")":
                depth -= 1
                if depth == 0:
                    close_at = k
                    break
        raw_params = split_top(sig[open_at + 1:close_at]) if open_at >= 0 else []
        params = [param_type(p) for p in raw_params]
        rest = sig[close_at + 1:] if close_at >= 0 else ""
        ret = rest.split("->", 1)[1].strip() if "->" in rest else ""
        # Body: following lines indented deeper than the fn, or blank.
        body = []
        j = i + 1
        while j < len(lines):
            c = strip_comment(lines[j])
            if c.strip():
                if len(c) - len(c.lstrip()) <= indent:
                    break
                body.append((j + 1, c))
            j += 1
        block = _leading_block(lines, start)
        exemptions = [parse_exemption(em.group(1)) for b in block if (em := EXEMPT_RE.match(b))]
        fns.append(Fn(
            name=m.group(3),
            line=start + 1,
            indent=indent,
            public=bool(m.group(2)),
            in_impl=impl_stack[-1][1] if impl_stack else None,
            params=params,
            ret=ret,
            body=body,
            is_test=any(TEST_ATTR_RE.match(b) for b in block),
            exemptions=exemptions,
            modes=[param_mode(p) for p in raw_params],
        ))
        i = j
    return fns, types, file_exempt


def _fn_sites(fn: Fn, types: set[str]) -> list[tuple[str, int, str]]:
    """(key, line, detail) of every candidate site in one fn, before exemptions."""
    out: list[tuple[str, int, str]] = []
    api = fn.in_impl == "inherent" or (fn.in_impl is None and fn.public)
    ret_int = fn.ret in INT_TYPES
    if api:
        if ret_int and is_predicate(fn.name):
            out.append(("bool-return", fn.line, f"-> {fn.ret}"))
        if ret_int and any(NEG_RETURN_RE.match(c) for _, c in fn.body):
            out.append(("sentinel-return", fn.line, f"-> {fn.ret}"))
        if ret_int and is_status(fn.body):
            out.append(("status-return", fn.line, f"-> {fn.ret}"))
        for (name, ty), mode in zip(fn.params, fn.modes or [""] * len(fn.params)):
            pointee = out_pointee(ty, mode)
            if name == "self" or pointee is None or not writes_back(pointee):
                continue
            # A C array of pointers (argv) is read by the kernel, not written.
            to_kernel = pointee[:1] not in ("*", "@")
            if any(assigns(c, name) or (to_kernel and hands_to_syscall(c, name))
                   for _, c in fn.body):
                sig = f"{name}:& {ty}" if mode == "&" else f"{name}: {ty}"
                out.append(("out-param", fn.line, sig))
        if fn.ret[:1] in ("*", "@") and any(NULL_RETURN_RE.match(c) for _, c in fn.body):
            out.append(("null-return", fn.line, f"-> {fn.ret}"))
        if RAW_RET_RE.search(fn.ret):
            out.append(("ptr-return", fn.line, f"-> {fn.ret}"))
        for k, (name, ty) in enumerate(fn.params):
            # A callback type with a raw `*T` makes every callback take one.
            for raw in fn_type_raw_params(ty):
                out.append(("raw-ptr-param", fn.line, f"{name}: {ty} ({raw})"))
            if name == "self" or not ty.startswith("*"):
                continue
            out.append(("raw-ptr-param", fn.line, f"{name}: {ty}"))
            if k + 1 < len(fn.params):
                nname, nty = fn.params[k + 1]
                if nty in INT_TYPES and (nname in LENGTH_NAMES or nname.endswith("_len")):
                    out.append(("ptr-len-param", fn.line, f"{name}: {ty}, {nname}: {nty}"))
    if fn.in_impl == "inherent" and fn.public and fn.params:
        name, ty = fn.params[0]
        if name == "self" and ty.startswith("*"):
            out.append(("raw-receiver", fn.line, f"self: {ty}"))
    if fn.in_impl is None and fn.public and fn.params:
        name, ty = fn.params[0]
        if name != "self" and base_type(ty) in types:
            out.append(("free-fn-method", fn.line, f"{name}: {ty}"))
    owner = fn.in_impl is not None or base_type(fn.ret) in types or (
        fn.params and base_type(fn.params[0][1]) in types)
    for ln, c in fn.body:
        if not owner:
            for m in ALLOC_RE.finditer(c):
                out.append(("raw-alloc", ln, m.group(1)))
        if fn.name != "main" and EXIT_RE.search(c):
            out.append(("lib-exit", ln, "sys_exit"))
    return out


def scan_source(text: str, path: str) -> list[Site]:
    fns, types, file_exempts = parse_fns(text)
    sites: list[Site] = []
    for fn in fns:
        if fn.is_test:
            continue
        file_exempt = [(ks, r) for ks, r, glob in file_exempts
                       if glob is None or fnmatch.fnmatchcase(fn.name, glob)]
        for ks, reason in fn.exemptions + file_exempt:
            if reason is None:
                sites.append(Site(MALFORMED, path, fn.line, fn.name,
                                  "standard-exempt needs known keys and a reason", None))
        for key, line, detail in _fn_sites(fn, types):
            reason = next((r for ks, r in fn.exemptions + file_exempt
                           if r is not None and key in ks), None)
            sites.append(Site(key, path, line, fn.name, detail, reason))
    return sites


def iter_sources(paths: list[Path]):
    for p in paths:
        if p.is_file():
            yield p
            continue
        for f in sorted(p.rglob("*.ritz")):
            if TEST_DIRS.intersection(f.relative_to(p).parts[:-1]):
                continue
            yield f


def scan_tree(paths: list[Path]) -> list[Site]:
    sites: list[Site] = []
    for f in iter_sources(paths):
        sites.extend(scan_source(f.read_text(errors="replace"), str(f)))
    return sites


# ---------------------------------------------------------------------------
# --callers (#4636): how far the exempt raw layer escapes the library.
# ---------------------------------------------------------------------------

IMPORT_RE = re.compile(r"^import\s+ritzlib\.([\w.]+)\s*(?:\{([^}]*)\}?)?")
CALL_RE = re.compile(r"(?<![\w.])(\w+)\s*\(")
# A method call: `.name(`.  exempt_apis keys an exempt method as ".name".
METHOD_RE = re.compile(r"\.(\w+)\s*\(")
DEF_RE = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?(?:extern\s+)?fn\s+")


@dataclass(frozen=True)
class CallSite:
    api: str
    path: str
    line: int


def exempt_apis(lib: Path) -> dict[str, set[str]]:
    """{name: {defining module, dotted from `lib`}} of every exempt API.

    An exempt API is a ``pub`` module-level fn with at least one exempt site,
    or a ``pub`` method of an inherent ``impl`` with one (#4688: ``push_cstr``
    and the other methods were missing from every pin).  A method is keyed
    ``".name"`` and counted at each ``.name(`` call in a file that imports its
    module.  The receiver type is not known, so a name that any ``pub`` method
    defines without an exemption is not counted, and a ``ptr-return`` method
    (an accessor such as ``as_ptr``) is not a C-string API and is not counted.
    """
    out: dict[str, set[str]] = {}
    accessors: set[str] = set()       # a method with a ptr-return exemption
    plain_methods: set[str] = set()   # a pub method of this name with no exemption
    for f in iter_sources([lib]):
        module = ".".join(f.relative_to(lib).with_suffix("").parts)
        text = f.read_text(errors="replace")
        fns, _, file_exempts = parse_fns(text)
        public = {fn.name for fn in fns if fn.public and fn.in_impl is None}
        methods = {fn.name for fn in fns if fn.public and fn.in_impl == "inherent"}
        plain_methods |= {fn.name for fn in fns if fn.public and fn.in_impl == "inherent"
                          and not fn.exemptions and not file_exempts}
        for s in scan_source(text, str(f)):
            if s.exempt is None:
                continue
            if s.fn in public:
                out.setdefault(s.fn, set()).add(module)
            if s.fn in methods and s.key == "ptr-return":
                accessors.add(s.fn)
            if s.fn in methods:
                out.setdefault("." + s.fn, set()).add(module)
    # A method call names no receiver type, so a name some other type defines
    # without an exemption (StrView.as_ptr beside String.as_ptr) would count
    # calls that are not exempt: leave that name out.
    for name in plain_methods | accessors:
        out.pop("." + name, None)
    return out


def _imports(lines: list[str]) -> dict[str, set[str] | None]:
    """{module: names listed, or None for the whole module} of a file's ritzlib imports."""
    out: dict[str, set[str] | None] = {}
    for ln in lines:
        m = IMPORT_RE.match(ln)
        if not m:
            continue
        mod, names = m.group(1), m.group(2)
        if names is None or "{" not in ln:
            out[mod] = None
        elif out.get(mod, set()) is not None:
            out.setdefault(mod, set()).update(n.strip() for n in names.split(",") if n.strip())
    return out


# Build output and caches: generated, untracked, and different per host.
SKIP_DIRS = {"build", "target"}


def _ritz_files(root: Path, skip: Path):
    """Every .ritz file under `root`, outside `skip`, hidden dirs and SKIP_DIRS.

    `skip`'s own tests/ is walked (AGAST #4928): the library's sources call
    its raw layer by design, but its tests are callers of its API like any
    other, and a test that goes around a Ritz-level API counts."""
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        if d != root and d.resolve() == skip:
            dirnames[:] = [n for n in dirnames if n == "tests"]
            continue
        dirnames[:] = sorted(n for n in dirnames if not n.startswith(".")
                             and n not in SKIP_DIRS)
        for n in sorted(filenames):
            if n.endswith(".ritz"):
                yield d / n


def count_callers(lib: Path, roots: list[Path],
                  apis: dict[str, set[str]] | None = None) -> list[CallSite]:
    """Every call of an exempt API of `lib` under `roots`, outside `lib`'s
    sources (`lib`/tests counts: see _ritz_files).

    `apis` ({name: {module}}) replaces the exempt set: #4638's memory pin
    also counts sys_mmap, which is raw but not exempt."""
    if apis is None:
        apis = exempt_apis(lib)
    skip = lib.resolve()
    sites: list[CallSite] = []
    for root in roots:
        for f in _ritz_files(root, skip):
            lines = f.read_text(errors="replace").split("\n")
            imports = _imports(lines)
            if not imports:
                continue
            for i, raw in enumerate(lines):
                if DEF_RE.match(raw):
                    continue
                code = strip_comment(raw)
                for m in CALL_RE.finditer(code):
                    name = m.group(1)
                    mods = apis.get(name)
                    if mods and any(mod in imports and (imports[mod] is None
                                                       or name in imports[mod])
                                    for mod in mods):
                        sites.append(CallSite(name, str(f), i + 1))
                for m in METHOD_RE.finditer(code):
                    name = "." + m.group(1)
                    mods = apis.get(name)
                    # A method is reached through its type, not imported by name:
                    # the module (or any `{...}` import of it) is enough.
                    if mods and any(mod in imports for mod in mods):
                        sites.append(CallSite(name, str(f), i + 1))
    return sites


def callers_by_project(sites: list[CallSite], root: Path) -> dict[str, int]:
    """Call counts grouped by the first directory under `root`."""
    out: dict[str, int] = {}
    for s in sites:
        rel = Path(s.path).relative_to(root)
        key = rel.parts[0] if len(rel.parts) > 1 else "."
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def callers_by_api(sites: list[CallSite]) -> dict[str, int]:
    out: dict[str, int] = {}
    for s in sites:
        out[s.api] = out.get(s.api, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def count_c_literals(line: str) -> int:
    """The `c"..."` literals that open on `line` (strings never span lines)."""
    n, i, end = 0, 0, len(line)
    while i < end:
        ch = line[i]
        if ch == "#":
            break
        if ch == "'":
            j = i + 2 if i + 1 < end and line[i + 1] == "\\" else i + 1
            if j + 1 < end and line[j + 1] == "'":
                i = j + 2
                continue
            i += 1
            continue
        if ch == '"':
            if i > 0 and line[i - 1] == "c" and (i < 2 or not (line[i - 2].isalnum()
                                                               or line[i - 2] == "_")):
                n += 1
            i += 1
            while i < end and line[i] != '"':
                i += 2 if line[i] == "\\" else 1
            i += 1
            continue
        i += 1
    return n


def c_literals_by_project(roots: list[Path]) -> dict[str, int]:
    """{project: `c"..."` literal count} over every .ritz file under `roots`."""
    out: dict[str, int] = {}
    for root in roots:
        for f in _ritz_files(root, Path("/nonexistent")):
            rel = f.relative_to(root)
            key = rel.parts[0] if len(rel.parts) > 1 else "."
            n = sum(count_c_literals(ln) for ln in f.read_text(errors="replace").split("\n"))
            out[key] = out.get(key, 0) + n
    return dict(sorted(out.items()))


def c_literal_breaches(counts: dict[str, int], pins: dict[str, int]) -> list[str]:
    """Projects whose `c"..."` count is above its pin (an unpinned project's pin is 0).

    Down-only: a count under its pin passes (lower the pin when you port).
    """
    return [f'{p}: {n} c"" literals > pin {pins.get(p, 0)}'
            for p, n in sorted(counts.items()) if n > pins.get(p, 0)]


def summarise(sites: list[Site]) -> dict[str, dict[str, int]]:
    out = {k: {"violations": 0, "exempt": 0} for k in [*RULES, MALFORMED]}
    for s in sites:
        out[s.key]["exempt" if s.exempt is not None else "violations"] += 1
    return out


# The C shapes #4636 pins down-only, per module (tools/test_standard_pins/).
# #4682 adds raw-receiver: a `self: *T` method reads as C's `T_m(T *p)`.
# ptr-return (#4689) is pinned apart, in test_standard_pins/test_cshape_ptr_return.py.
C_SHAPE_KEYS = ("bool-return", "status-return", "out-param", "raw-receiver")


def ratchet_breaches(summary: dict[str, dict[str, int]],
                     pins: dict[str, tuple[int, int]]) -> list[str]:
    """What `summary` has above `pins` = {key: (violations, violations + exempt)}.

    A down-only ratchet: a count under its pin passes (a migration lowered
    it; tighten the pin when convenient), a count over it is a new C-shaped
    site.  Exempting a site keeps the total and lowers the violations, so it
    passes; a new site, exempt or not, raises the total and fails.  A key
    with no pin is pinned at (0, 0).
    """
    out = []
    for key in C_SHAPE_KEYS:
        v = summary[key]["violations"]
        total = v + summary[key]["exempt"]
        pv, ptotal = pins.get(key, (0, 0))
        if v > pv:
            out.append(f"{key}: {v} violations > pin {pv}")
        if total > ptotal:
            out.append(f"{key}: {total} sites (violations + exempt) > pin {ptotal}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    ap.add_argument("--list", metavar="KEY", choices=[*RULES, MALFORMED],
                    help="list every site of one counting rule")
    ap.add_argument("--callers", action="store_true",
                    help="count calls of the library's exempt APIs under PATHs (default: projects/)")
    ap.add_argument("--lib", type=Path, help="the library for --callers (default: ritzlib)")
    ap.add_argument("--c-literals", action="store_true",
                    help='count c"..." literals per project under PATHs (default: projects/)')
    args = ap.parse_args(argv)
    ritz = Path(__file__).resolve().parent.parent
    if args.c_literals:
        counts = c_literals_by_project(args.paths or [ritz.parent])
        if args.json:
            print(json.dumps({"total": sum(counts.values()), "by_project": counts}, indent=2))
            return 0
        print(f'c"..." literals: {sum(counts.values())} (STANDARD.md S-TEXT-1)')
        for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {v:>6}  {k}")
        return 0
    if args.callers:
        return _main_callers(args.lib or ritz / "ritzlib", args.paths or [ritz.parent], args.json)
    paths = args.paths or [ritz / "ritzlib"]
    sites = scan_tree(paths)
    if args.list:
        for s in sites:
            if s.key == args.list:
                tag = f"  [exempt: {s.exempt}]" if s.exempt is not None else ""
                print(f"{s.path}:{s.line}: {s.fn}: {s.detail}{tag}")
        return 0
    summary = summarise(sites)
    if args.json:
        print(json.dumps(summary, indent=2))
        return 0
    files = sum(1 for _ in iter_sources(paths))
    print(f"docs/STANDARD.md conformance over {files} file(s): {', '.join(map(str, paths))}")
    print(f"{'rule':<11} {'key':<17} {'violations':>10} {'exempt':>7}  what")
    for key, (rule, what) in RULES.items():
        c = summary[key]
        print(f"{rule:<11} {key:<17} {c['violations']:>10} {c['exempt']:>7}  {what}")
    c = summary[MALFORMED]
    print(f"{'-':<11} {MALFORMED:<17} {c['violations']:>10} {'':>7}  standard-exempt without known keys and a reason")
    return 0


def _main_callers(lib: Path, roots: list[Path], as_json: bool) -> int:
    sites = count_callers(lib, roots)
    by_project: dict[str, int] = {}
    for root in roots:
        for k, v in callers_by_project([s for s in sites if Path(s.path).is_relative_to(root)],
                                       root).items():
            by_project[k] = by_project.get(k, 0) + v
    by_api = callers_by_api(sites)
    if as_json:
        print(json.dumps({"total": len(sites), "by_project": by_project, "by_api": by_api},
                         indent=2))
        return 0
    print(f"exempt {lib.name} APIs called outside it: {len(sites)} call site(s)")
    print("by project:")
    for k, v in sorted(by_project.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {v:>6}  {k}")
    print("by API:")
    for k, v in by_api.items():
        print(f"  {v:>6}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

