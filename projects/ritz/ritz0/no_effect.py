"""A statement with no effect is refused (LARB R64; AGAST #3491).

An expression whose value is discarded is an error when its outermost node is
a literal, name, field, index, borrow, `*p`, cast, aggregate literal or
operator: it computes something and throws it away.  A string gets a hint,
since that slip is a print that was never written (259 zeus `"FAIL: …"` lines,
#3490).  Calls, assignments and `if`/`match`/blocks are allowed; a discarded
`[[must_use]]` call is §17.8's (emitter_llvmlite._reject_discarded_must_use).

Where a value is discarded (R69: a block has a value only when it is used as
one):

* every expression statement;
* the last line of a void fn, a `while`/`for`/`loop` body, an `unsafe` or
  `defer` body;
* inside a discarded `if`, `match` or block: each branch's last line, each
  arm's body.

A bare `pass` is the no-op (test_pass_is_an_identifier.py), never a name read.
Syntactic, like reachability, but run after the typing pass: where that pass
already refused the expression with a slot error (a whole array alone, #3189,
in ritz1's words), that more specific error stands and this one stays quiet;
the emitter reports it.  Still before monomorphisation, so a generic fn is
judged whether or not it's used.
ritz1's twin is #3492.
"""

import re
from dataclasses import fields, is_dataclass
from typing import Dict, List, Optional, Set, Tuple

import ritz_ast as rast
from binder_names import _judged_fns

STRING_HINT = "a string on its own line prints nothing: call print"

# The outermost nodes that do nothing but compute a value (R64).
_NO_EFFECT = (
    rast.IntLit, rast.FloatLit, rast.StringLit, rast.CStringLit,
    rast.InterpString, rast.CharLit, rast.BoolLit, rast.NullLit,  # literals
    rast.Ident, rast.QualifiedIdent,                               # names
    rast.Field, rast.Index, rast.SliceExpr,                        # places
    rast.Cast,
    rast.StructLit, rast.ArrayLit, rast.ArrayFill, rast.TupleLit,  # aggregates
    rast.BinOp, rast.UnaryOp, rast.Range,                          # operators; @x, *p
)
_STRINGS = (rast.StringLit, rast.CStringLit, rast.InterpString)
_WORD = re.compile(r'\w+')


def no_effect_message(text: str, is_string: bool) -> str:
    """The ruling's words for a discarded `text`."""
    message = f"statement has no effect: the value of `{text}` is discarded"
    return f"{message}; {STRING_HINT}" if is_string else message


class _Source:
    """The source text of an expression, from its file, by its start.

    A Span holds only where a node starts, so the text runs to the end of
    its logical line: the next newline outside brackets, or a `#` comment,
    or before then to a bracket it didn't open or an inline `if` arm's
    `else` (one no `if` in the text opened).
    """

    def __init__(self) -> None:
        self._lines: Dict[str, Optional[List[str]]] = {}

    def text(self, span) -> Optional[str]:
        lines = self._file(span.file)
        if lines is None or not 0 < span.line <= len(lines):
            return None
        out, depth, quote, open_ifs = [], 0, None, 0
        line, col = span.line - 1, span.column - 1
        while line < len(lines):
            src = lines[line]
            while col < len(src):
                ch = src[col]
                if quote:
                    out.append(ch)
                    if ch == '\\' and col + 1 < len(src):
                        col += 1
                        out.append(src[col])
                    elif ch == quote:
                        quote = None
                elif ch in '"\'':
                    quote = ch
                    out.append(ch)
                elif ch == '#':
                    break
                elif ch in ')]}' and depth == 0:
                    # Closes a group the expression sits in: `(if c then ^x)`.
                    return self._joined(out)
                elif depth == 0 and (ch.isalpha() or ch == '_') and not (
                        col and (src[col - 1].isalnum() or src[col - 1] == '_')):
                    word = _WORD.match(src, col).group()
                    if word == 'else' and not open_ifs:
                        # An inline `if` arm's end: `if c then ^x else y`.
                        return self._joined(out)
                    open_ifs += (word == 'if') - (word == 'else')
                    out.append(word)
                    col += len(word)
                    continue
                else:
                    depth += ch in '([{'
                    depth -= ch in ')]}'
                    out.append(ch)
                col += 1
            if depth <= 0:
                break
            out.append(' ')
            line, col = line + 1, 0
        return self._joined(out)

    @staticmethod
    def _joined(out: List[str]) -> Optional[str]:
        return ' '.join(''.join(out).split()) or None

    def _file(self, path: str) -> Optional[List[str]]:
        if path not in self._lines:
            try:
                with open(path, encoding='utf-8') as f:
                    self._lines[path] = f.read().split('\n')
            except (OSError, UnicodeDecodeError, TypeError):
                self._lines[path] = None
        return self._lines[path]


_Where = Tuple[str, int, int]


def _where(span) -> Optional[_Where]:
    return None if span is None else (span.file, span.line, span.column)


class _Judge:
    def __init__(self, refused: Set[_Where]) -> None:
        self.errors: List[str] = []
        self._source = _Source()
        # Where the typing pass already put a slot error (#3189's whole array).
        self._refused = refused

    def discarded(self, expr: Optional[rast.Expr]) -> None:
        """`expr`'s value is thrown away: refuse it if it has no effect."""
        if expr is None:
            return
        if isinstance(expr, rast.If):
            self.discarded(expr.then_block.expr)
            if expr.else_block is not None:
                self.discarded(expr.else_block if isinstance(expr.else_block, rast.If)
                               else expr.else_block.expr)
            return
        if isinstance(expr, rast.Match):
            for arm in expr.arms:
                self.discarded(arm.body)
            return
        if isinstance(expr, rast.Block):
            self.discarded(expr.expr)
            return
        if isinstance(expr, rast.Ident) and expr.name == 'pass':
            return
        inner = expr
        while isinstance(inner, rast.Grouped):
            inner = inner.expr
        if not isinstance(inner, _NO_EFFECT) or expr.span is None:
            return
        if _where(expr.span) in self._refused or _where(inner.span) in self._refused:
            return
        sp = expr.span
        text = self._source.text(sp) or type(inner).__name__
        message = no_effect_message(text, isinstance(inner, _STRINGS))
        self.errors.append(f"{sp.file}:{sp.line}:{sp.column}: error: {message}")

    def walk(self, node) -> None:
        """Every discard point under `node`, in source order."""
        if isinstance(node, rast.ExprStmt):
            self.discarded(node.expr)
        elif isinstance(node, (rast.WhileStmt, rast.ForStmt, rast.UnsafeBlock,
                               rast.DeferStmt)):
            self.discarded(node.body.expr)
        for f in fields(node):
            if f.name == 'span':
                continue
            value = getattr(node, f.name, None)
            for item in (value if isinstance(value, (list, tuple)) else (value,)):
                if isinstance(item, rast.Node) and is_dataclass(item):
                    self.walk(item)


def _returns_nothing(fn: rast.FnDef) -> bool:
    ret = fn.ret_type
    return ret is None or (isinstance(ret, rast.NamedType) and ret.name == 'void'
                           and not ret.args)


def check_no_effect(module: rast.Module, source_path: Optional[str] = None,
                    typed=None) -> List[str]:
    """`file:line:col: error: statement has no effect: …` for each discarded
    no-effect expression in the fns this compile emits.  `typed` is the typing
    pass's table (typed.Typed): its slot errors' places are left to it."""
    refused = {_where(e.span) for e in (typed.slot_errors if typed is not None else ())}
    judge = _Judge(refused - {None})
    for fn in _judged_fns(module, source_path):
        if _returns_nothing(fn):
            judge.discarded(fn.body.expr)
        judge.walk(fn.body)
    return judge.errors
