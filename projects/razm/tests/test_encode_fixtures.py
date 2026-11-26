"""The encode tests' expected bytes are what `as --64` writes today.

The Ritz tests (test/test_encode_*.ritz) compare razm's encoder with
committed bytes, so they need no `as`. This test re-derives those bytes from
`as` and fails when one is stale; `python3 tests/encode_fixtures.py`
rewrites them.
"""

from __future__ import annotations

from encode_fixtures import PKG, TEST_GLOB, cases, run


def test_encode_fixtures_have_cases():
    paths = sorted(PKG.glob(TEST_GLOB))
    assert paths, f"no {TEST_GLOB}"
    assert len(cases(paths)) > 100


def test_encode_fixtures_match_as():
    problems = run(sorted(PKG.glob(TEST_GLOB)), check=True)
    assert problems == [], "\n".join(problems)
