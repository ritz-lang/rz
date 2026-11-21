"""AGAST #3450 (LARB review/5 ritz0 N6): one escape table for every literal.

The escape ladder (\\n \\t \\r \\\\ \\" \\') used to be written out once in
`_lex_string` and again in `_lex_cstring`. #1872 folded both into
`lexer._ESCAPES` / `decode_escape`; these tests keep it that way:

* every literal kind decodes through the same table, so changing one entry
  changes "...", '.' and c"..." together (a re-grown private ladder would
  ignore the patch and fail here), and
* `_lex_string` stays at or under the review's complexity bound of 30
  (ritz-metrics measured it at 44 in review/5 and 35 after #1872).
"""

import importlib.util
import sys
from pathlib import Path

import lexer
import pytest
from lexer import tokenize
from tokens import TokenType

RITZ0_DIR = Path(__file__).resolve().parents[1]
METRICS = RITZ0_DIR.parents[1] / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"

# LARB review/5 ritz0.md N6 acceptance.
LEX_STRING_CC_MAX = 30


def _literal(src):
    """The value of the first token of `src`, a single literal."""
    tok = tokenize(src)[0]
    return tok.type, tok.value


@pytest.mark.unit
@pytest.mark.parametrize("esc", sorted(lexer._ESCAPES))
def test_every_literal_kind_reads_the_shared_table(monkeypatch, esc):
    """Re-point one table entry: all three literal kinds must follow it."""
    monkeypatch.setitem(lexer._ESCAPES, esc, "Z")
    assert _literal(f'"a\\{esc}b"') == (TokenType.STRING, "aZb")
    assert _literal(f'c"a\\{esc}b"') == (TokenType.CSTRING, "aZb")
    assert _literal(f"'\\{esc}'") == (TokenType.CHAR, ord("Z"))


@pytest.mark.unit
def test_interpolated_literal_reads_the_shared_table(monkeypatch):
    """The `{...}` path cooks its plain value via `_cook_plain`: same table."""
    monkeypatch.setitem(lexer._ESCAPES, "n", "Z")
    tok = tokenize('"a\\n{x}"')[0]
    assert tok.value == "aZ{x}"


@pytest.mark.unit
def test_lex_string_complexity_within_bound(monkeypatch):
    spec = importlib.util.spec_from_file_location("ritz_metrics", METRICS)
    metrics = importlib.util.module_from_spec(spec)
    # @dataclass resolves annotations through sys.modules[cls.__module__].
    monkeypatch.setitem(sys.modules, "ritz_metrics", metrics)
    spec.loader.exec_module(metrics)
    path = Path(lexer.__file__)
    fns = metrics.extract_functions(path, path.read_text().splitlines(), "py")
    (fn,) = [f for f in fns if f.name == "_lex_string"]
    assert fn.complexity <= LEX_STRING_CC_MAX, (
        f"_lex_string cyclomatic complexity {fn.complexity} > {LEX_STRING_CC_MAX} "
        f"(LARB review/5 N6): move a branch body into a helper")
