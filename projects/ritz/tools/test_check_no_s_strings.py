"""Unit tests for check_no_s_strings.py.

Covers the string-stripping pre-filter plus a handful of real-world edge
cases (literal inside a c"...", `s"` at start-of-line, `s"` after common
delimiters, false-positive shapes that must NOT trip).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_no_s_strings import S_STRING_RE, find_violations, strip_string_content


class TestStripStringContent:
    def test_preserves_plain_code(self):
        assert strip_string_content('let x = 42') == 'let x = 42'

    def test_blanks_string_body(self):
        # Opens + closes quote remain; interior is blanked.
        assert strip_string_content('x = "hello"') == 'x = "     "'

    def test_blanks_cstring_body_so_s_inside_is_not_a_hit(self):
        out = strip_string_content('x = c"is this s\\"broken"')
        assert S_STRING_RE.search(out) is None

    def test_comment_to_eol(self):
        out = strip_string_content('let x = 5  # s"comment"')
        assert S_STRING_RE.search(out) is None


class TestRegex:
    @pytest.mark.parametrize('src', [
        'let s: StrView = s"hello"',
        's"hello"',
        '[s"a", s"b"]',
        '(s"x")',
        'foo(s"arg")',
        'x={s"one"}',
    ])
    def test_positive(self, src: str):
        assert S_STRING_RE.search(strip_string_content(src)) is not None, src

    @pytest.mark.parametrize('src', [
        'let s: u8 = 0',                     # no `s"` at all
        'c"contains s and quotes"',          # s inside a c-string
        'foo_s"bar"',                        # identifier ending in s (not legal syntax, but mustn't false-positive)
        '# s"in a comment"',                 # comment
        'let s = "hello"',                   # bare string, variable literally named s
        'pass_s(arg)',                       # identifier prefix
    ])
    def test_negative(self, src: str):
        assert S_STRING_RE.search(strip_string_content(src)) is None, src


class TestFindViolations:
    def _setup(self, files: dict[str, str]) -> Path:
        tmpdir = Path(tempfile.mkdtemp(prefix='check_no_s_strings_'))
        for name, body in files.items():
            path = tmpdir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        return tmpdir

    def test_clean_tree(self):
        root = self._setup({
            'a.ritz': 'let x = "hello"\n',
            'sub/b.ritz': 'let y: *u8 = c"world"\n',
        })
        assert find_violations(root) == []

    def test_catches_s_string(self):
        root = self._setup({'a.ritz': 'let v = s"bad"\n'})
        viols = find_violations(root)
        assert len(viols) == 1
        assert viols[0][1] == 1  # lineno
        assert 's"bad"' in viols[0][2]

    def test_skips_archive(self):
        root = self._setup({
            'live/a.ritz': 'x = s"live"\n',
            'docs/archive/old.ritz': 'x = s"archived"\n',
        })
        viols = find_violations(root)
        assert len(viols) == 1
        assert 'live' in str(viols[0][0])

    def test_skips_comments_and_string_content(self):
        # The non-archived file has `s"` in string content and in a comment —
        # both must be ignored. No live violations → no hits.
        root = self._setup({
            'a.ritz': (
                '# discussion of s"..." lives in comments\n'
                'let msg = c"the s\\"-prefix was removed"\n'
            ),
        })
        assert find_violations(root) == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
