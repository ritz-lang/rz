"""AGAST #4450: ritz1 tests a kind with `match`, not an if-ladder.

ritz1's kind codes are the C-style enums ExprKind, StmtKind, OpKind and
TypeKind (ritz1/src/ast.ritz).  A *kind ladder* is two or more tests, in one
block, of the same scrutinee S against `E.V` (E one of those enums), as

- (a) consecutive links of an `if` / `else if` chain, or
- (b) consecutive sibling `if`s (no `else`) whose bodies all leave the block:
  their last statement is `return`, `break` or `continue`.

A test counts when it is pure: `S == E.V`, or an `or` of those on one S,
optionally parenthesised.  `!=`, `and` or any other term makes it no arm,
and it ends a ladder.  A ladder is written as a `match S` instead: the
compiler then checks the arms are distinct and covered, and a reader sees
one scrutinee instead of re-reading S on every line.

The generated parser_gen.ritz / lexer_scan_gen.ritz / tokens_gen.ritz are
not scanned: ritzgen writes them.

An `or` test becomes one or-pattern arm, `E.A | E.B =>` (LANGUAGE_SPEC §8.2).
Every ladder was converted, so there is no allowlist: none may come back.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS.parent / "ritz1" / "src"

GENERATED = frozenset({"parser_gen.ritz", "lexer_scan_gen.ritz", "tokens_gen.ritz"})
ENUMS = ("ExprKind", "StmtKind", "OpKind", "TypeKind")

_TEST = re.compile(r"^(.+?)\s*==\s*(" + "|".join(ENUMS) + r")\.[A-Za-z_]\w*$")
_LEAVE = re.compile(r"^(return|break|continue)\b")


def _code(line: str) -> str:
    """`line` without its `#` comment; `#` inside a string or char stays."""
    out, i, q = [], 0, None
    while i < len(line):
        c = line[i]
        if q:
            if c == "\\":
                out.append(line[i:i + 2])
                i += 2
                continue
            if c == q:
                q = None
        elif c == "#":
            break
        elif c == '"':
            q = c
        elif c == "'":
            m = re.match(r"'(\\.|[^'\\])'", line[i:])
            if m:
                out.append(m.group(0))
                i += m.end()
                continue
        out.append(c)
        i += 1
    return "".join(out).rstrip()


def _unparen(s: str) -> str:
    s = s.strip()
    while s.startswith("(") and s.endswith(")"):
        depth = 0
        for i, c in enumerate(s):
            depth += (c == "(") - (c == ")")
            if depth == 0 and i < len(s) - 1:
                return s          # `(a) or (b)`: the outer parens don't pair
        s = s[1:-1].strip()
    return s


def _split_or(s: str) -> list[str]:
    parts, depth, last = [], 0, 0
    for m in re.finditer(r"[()]|\bor\b", s):
        if m.group() == "(":
            depth += 1
        elif m.group() == ")":
            depth -= 1
        elif depth == 0:
            parts.append(s[last:m.start()])
            last = m.end()
    return parts + [s[last:]]


def pure_test(cond: str) -> tuple[str, str] | None:
    """(S, enum) when `cond` is a pure kind test, else None."""
    cond = _unparen(cond)
    if re.search(r"\band\b", cond):
        return None
    key = None
    for part in _split_or(cond):
        m = _TEST.match(_unparen(part))
        if not m:
            return None
        k = (re.sub(r"\s+", " ", m.group(1).strip()), m.group(2))
        if key not in (None, k):
            return None
        key = k
    return key


def ladders(text: str) -> list[tuple[int, str]]:
    """(1-based line, first test's text) of every kind ladder in `text`."""
    raw = text.splitlines()
    code = [_code(l) for l in raw]
    n = len(code)

    def ind(i: int) -> int:
        return len(code[i]) - len(code[i].lstrip(" "))

    def body_end(h: int) -> int:
        # past the last code line deeper than the header
        d, j, last = ind(h), h + 1, h
        while j < n:
            if code[j].strip():
                if ind(j) <= d:
                    break
                last = j
            j += 1
        return last + 1

    def next_code(j: int) -> int:
        while j < n and not code[j].strip():
            j += 1
        return j

    def chain(i: int) -> list[tuple[int, str | None, int]]:
        """[(header line, condition or None for else, body end)]."""
        d, links, h, cond = ind(i), [], i, code[i].strip()[3:]
        while True:
            end = body_end(h)
            links.append((h, cond, end))
            j = next_code(end)
            if cond is None or j >= n or ind(j) != d:
                return links
            s = code[j].strip()
            if s.startswith("else if "):
                h, cond = j, s[8:]
            elif s == "else":
                h, cond = j, None
            else:
                return links

    def leaves(h: int, end: int) -> bool:
        body = [k for k in range(h + 1, end) if code[k].strip()]
        top = [k for k in body if ind(k) == ind(h) + 4]
        return bool(top) and bool(_LEAVE.match(code[top[-1]].strip()))

    found = []
    chains = {i: chain(i) for i in range(n) if code[i].lstrip().startswith("if ")}
    # (a) a run of two or more pure links of one chain, on one scrutinee
    for links in chains.values():
        tests = [(h, pure_test(c)) for h, c, _ in links if c is not None]
        k = 0
        while k < len(tests):
            j = k + 1
            while tests[k][1] and j < len(tests) and tests[j][1] == tests[k][1]:
                j += 1
            if tests[k][1] and j - k >= 2:
                found.append(tests[k][0])
            k = j
    # (b) a run of two or more lone, leaving `if`s on one scrutinee
    def lone(links: list) -> tuple[str, str] | None:
        """The test of an `if` with no `else` whose body leaves, if pure."""
        if len(links) != 1 or not leaves(links[0][0], links[0][2]):
            return None
        return pure_test(links[0][1])

    taken: set[int] = set()
    for i in sorted(chains):
        if i in taken:
            continue
        key = lone(chains[i])
        if key is None:
            continue
        run, end = [i], chains[i][0][2]
        while True:
            j = next_code(end)
            if j >= n or j not in chains or ind(j) != ind(i) or lone(chains[j]) != key:
                break
            run.append(j)
            end = chains[j][0][2]
        taken.update(run)
        if len(run) >= 2:
            found.append(i)
    return [(h + 1, code[h].strip()) for h in sorted(found)]


def scan(src: Path = SRC) -> list[tuple[str, int, str]]:
    """(file, line, first test) of every ladder in ritz1/src."""
    out = []
    for path in sorted(src.glob("*.ritz")):
        if path.name not in GENERATED:
            out += [(path.name, ln, t) for ln, t in ladders(path.read_text())]
    return out


# -------------------------------------------------------------- self-test

CHAIN = """\
fn f(e: *Expr) -> i32
    if e.kind == ExprKind.Call
        return 1
    else if e.kind == ExprKind.Index   # a comment
        x = 2
    else
        x = 3
    x
"""

SIBLINGS = """\
fn f(k: TypeKind) -> i32
    if k == TypeKind.I8
        return 1
    if (k == TypeKind.I16 or k == TypeKind.U16)
        return 2
    0
"""

NOT_ARMS = """\
fn f(k: TypeKind, b: bool) -> i32
    if k != TypeKind.I8
        return 1
    if k == TypeKind.I16 and b
        return 2
    if k == TypeKind.I8
        x = 1
    else if k == TypeKind.I32 and b
        x = 2
    if k == TypeKind.I8
        return 5
    0
"""


@pytest.mark.unit
def test_scanner_catches_a_chain():
    assert ladders(CHAIN) == [(2, "if e.kind == ExprKind.Call")]


@pytest.mark.unit
def test_scanner_catches_sibling_returns():
    assert ladders(SIBLINGS) == [(2, "if k == TypeKind.I8")]


@pytest.mark.unit
def test_scanner_skips_impure_tests_and_single_tests():
    # `!=` and `and` are no arms; a lone `k == I8` test is no ladder; a
    # non-leaving body ends a sibling run; two scrutinees are two runs.
    assert ladders(NOT_ARMS) == []
    assert ladders(SIBLINGS.replace("k == TypeKind.I16", "j == TypeKind.I16")) == []
    assert ladders(CHAIN.replace("        return 1\n", "        x = 1\n", 1)
                   .replace("\n    else if", "\n    if", 1)) == []


@pytest.mark.unit
def test_no_kind_ladders_in_ritz1():
    bad = [f"{f}:{ln}: {t}" for f, ln, t in scan()]
    assert not bad, (
        "test a kind with `match` (LANGUAGE_SPEC §8), not an if-ladder; "
        "an `or` test is an `A | B =>` arm and the `else`/fallthrough is `_`:\n" + "\n".join(bad))
