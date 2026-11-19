"""The typing pass: a `"…"` literal in a `Span<u8>` slot (AGAST #3596).

LARB R62 and LANGUAGE_SPEC §3.5: in a `Span<u8>` slot a `"…"` literal is a
`Span<u8>` of its bytes; a `StrView` value, a `c"…"` literal and a `String`
don't convert. The typing pass gave the literal StrView whatever the slot, so
every slot form was refused while the emitter compiled it.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from parser import parse
from type_checker import TypeChecker


def types(source: str) -> list:
    return [str(e) for e in TypeChecker().check(parse(source))]


HOLDER = "struct Holder\n    s: Span<u8>\n\n"
TAKE = "fn take(s: Span<u8>) -> i64\n    s.len\n\n"


class TestLiteralFitsSpanU8:
    """Each slot form the checker reaches by its own path."""

    @pytest.mark.parametrize("body", [
        pytest.param('    let s: Span<u8> = "abc"\n    0\n', id="let"),
        pytest.param('    var s: Span<u8> = "abc"\n    0\n', id="var"),
        pytest.param('    var s: Span<u8> = "a"\n    s = "bc"\n    0\n', id="assign"),
        pytest.param('    take("abc") as i32\n', id="argument"),
        pytest.param('    let h = Holder { s: "abc" }\n    0\n', id="field"),
        pytest.param('    let a: [2]Span<u8> = ["a", "bcd"]\n    0\n', id="array-element"),
    ])
    def test_slot(self, body):
        assert types(HOLDER + TAKE + "fn main() -> i32\n" + body) == []

    def test_return(self):
        assert types('fn f() -> Span<u8>\n    return "abcd"\n') == []

    def test_tail_through_if(self):
        src = 'fn f(b: bool) -> Span<u8>\n    if b\n        "ab"\n    else\n        "cd"\n'
        assert types(src) == []


class TestStillRefused:
    """Only a `"…"` literal converts, and only to `Span<u8>`."""

    def test_strview_value(self):
        src = 'fn main() -> i32\n    let v: StrView = "abc"\n    let s: Span<u8> = v\n    0\n'
        assert any("cannot initialize Span<u8> with StrView" in e for e in types(src))

    def test_c_literal(self):
        src = 'fn main() -> i32\n    let s: Span<u8> = c"abc"\n    0\n'
        assert any("cannot initialize Span<u8>" in e for e in types(src))

    def test_other_element_type(self):
        src = 'fn main() -> i32\n    let s: Span<i32> = "abc"\n    0\n'
        assert any("cannot initialize Span<i32> with StrView" in e for e in types(src))

    def test_mixed_tails_judge_the_non_literal(self):
        src = ('fn f(b: bool, v: StrView) -> Span<u8>\n    if b\n        "ab"\n'
               '    else\n        v\n')
        assert types(src) != []


@pytest.mark.integration
def test_corpus_sites_type_check():
    """The 27 findings #2229 measured, through ritz0.py's wiring."""
    here = Path(__file__).parent
    files = ["test_cs_mixed", "test_sstring", "test_strlit_span_slot_no_import",
             "test_strlit_span_slot_strview"]
    for name in files:
        result = subprocess.run(
            [sys.executable, str(here / "ritz0.py"), str(here / "test" / f"{name}.ritz"),
             "-o", "/dev/null", "--check-names"],
            capture_output=True, text=True, env={"RITZ_PATH": str(here.parent)},
            cwd=here.parent)
        assert result.returncode == 0, f"{name}: {result.stderr}"
