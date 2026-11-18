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

THE COUNTING RULES (each is the "Report:" line of a rule in STANDARD.md)
-----------------------------------------------------------------------

"API fn" means a ``pub fn`` at module level, or any fn in an inherent
``impl Type`` block.  Fns in a trait impl (``impl Drop for T``) are skipped
for the signature rules, because the trait fixes their signature.  Test
directories (``tests/``, ``test/``) and ``[[test]]`` / ``[[test_helper]]``
fns are never counted.

  bool-return      API fn with an integer return whose name is a predicate:
                   a ``_``-separated word in PREDICATE_WORDS, or a name
                   ending in ``eq`` (``streq``, ``memeq``).
  sentinel-return  API fn with an integer return whose body has
                   ``return -<digit>``.
  null-return      API fn returning ``*T``/``@T``/``@&T`` whose body has
                   ``return null``.
  raw-ptr-param    each ``*T`` parameter of an API fn.
  ptr-len-param    API fn with a ``*T`` parameter followed directly by an
                   integer parameter named in LENGTH_NAMES or ending in
                   ``_len``.
  free-fn-method   a public module-level fn whose first parameter's type,
                   with references, pointers and generics stripped, is a
                   struct or enum declared in the same file.
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

A reason under MIN_REASON characters, or a key that isn't a counting rule,
is itself counted, as ``exempt-malformed``.  Exempt sites are still listed
and counted, in their own column, so exemptions can't pile up unseen.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# key -> (rule ID in docs/STANDARD.md, one-line description)
RULES: dict[str, tuple[str, str]] = {
    "bool-return": ("S-BOOL-2", "predicate returns an integer, not bool"),
    "sentinel-return": ("S-RESULT-1", "failure signalled by a negative integer return"),
    "null-return": ("S-OPTION-1", "absence signalled by returning null"),
    "raw-ptr-param": ("S-PTR-1", "raw *T parameter on an API fn"),
    "ptr-len-param": ("S-PTR-2", "(*T, length) pair instead of Span<T>/StrView"),
    "free-fn-method": ("S-IMPL-1", "free fn on a type this module declares"),
    "raw-alloc": ("S-OWN-2", "raw allocation outside the owning type"),
    "lib-exit": ("S-ERR-3", "library code ends the program"),
}
MALFORMED = "exempt-malformed"
MIN_REASON = 12

INT_TYPES = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "isize", "usize"}
PREDICATE_WORDS = {
    "is", "has", "can", "contains", "exists", "eq", "equals", "starts", "ends",
    "valid", "empty", "matches",
}
LENGTH_NAMES = {"len", "n", "size", "count", "cap", "nbytes", "length"}
ALLOC_FNS = ("malloc", "free", "realloc", "calloc", "heap_alloc", "heap_free",
             "heap_realloc", "sys_mmap", "sys_munmap", "mmap", "munmap")

ALLOC_RE = re.compile(r"(?<![\w.])(" + "|".join(ALLOC_FNS) + r")\s*\(")
EXIT_RE = re.compile(r"(?<![\w.])sys_exit\s*\(")
NEG_RETURN_RE = re.compile(r"^\s*return\s+-\s*\d")
NULL_RETURN_RE = re.compile(r"^\s*return\s+null\b")
FN_RE = re.compile(r"^(\s*)(pub\s+)?(?:async\s+)?fn\s+(\w+)")
TYPE_DECL_RE = re.compile(r"^(?:pub\s+)?(struct|enum)\s+(\w+)")
IMPL_RE = re.compile(r"^(\s*)impl\b(?:<[^>]*>)?\s*(.*)$")
EXEMPT_RE = re.compile(r"^\s*#\s*standard-exempt:\s*(.*)$")
EXEMPT_FILE_RE = re.compile(r"^\s*#\s*standard-exempt-file:\s*(.*)$")
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
    return bool(PREDICATE_WORDS.intersection(words)) or name.endswith("eq")


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


def parse_fns(text: str) -> tuple[list[Fn], set[str], list[tuple[set[str], str | None]]]:
    lines = text.split("\n")
    types = {m.group(2) for ln in lines if (m := TYPE_DECL_RE.match(ln))}
    file_exempt = []
    for ln in lines:
        s = ln.strip()
        if s and not s.startswith("#"):
            break
        if m := EXEMPT_FILE_RE.match(ln):
            file_exempt.append(parse_exemption(m.group(1)))

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
        params = [param_type(p) for p in split_top(sig[open_at + 1:close_at])] if open_at >= 0 else []
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
        if fn.ret[:1] in ("*", "@") and any(NULL_RETURN_RE.match(c) for _, c in fn.body):
            out.append(("null-return", fn.line, f"-> {fn.ret}"))
        for k, (name, ty) in enumerate(fn.params):
            if name == "self" or not ty.startswith("*"):
                continue
            out.append(("raw-ptr-param", fn.line, f"{name}: {ty}"))
            if k + 1 < len(fn.params):
                nname, nty = fn.params[k + 1]
                if nty in INT_TYPES and (nname in LENGTH_NAMES or nname.endswith("_len")):
                    out.append(("ptr-len-param", fn.line, f"{name}: {ty}, {nname}: {nty}"))
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
    fns, types, file_exempt = parse_fns(text)
    sites: list[Site] = []
    for fn in fns:
        if fn.is_test:
            continue
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


def summarise(sites: list[Site]) -> dict[str, dict[str, int]]:
    out = {k: {"violations": 0, "exempt": 0} for k in [*RULES, MALFORMED]}
    for s in sites:
        out[s.key]["exempt" if s.exempt is not None else "violations"] += 1
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    ap.add_argument("--list", metavar="KEY", choices=[*RULES, MALFORMED],
                    help="list every site of one counting rule")
    args = ap.parse_args(argv)
    paths = args.paths or [Path(__file__).resolve().parent.parent / "ritzlib"]
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


if __name__ == "__main__":
    sys.exit(main())

