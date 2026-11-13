"""One ritz0 compile lexes and parses each source once (AGAST #2807).

Profiling for #2793 found `Lexer.tokenize` running 5 times and
`Parser.parse_module` 3 times per compile of a one-file program: once for
compile_file's parse, then twice each in fn_cache.build_hash_map and
build_sig_hash_map (a parse, then a second lex for the raw tokens to hash,
since the parser splits `>>`/`>=` in the list it is given). The lexer was ~30%
of a small compile.

compile_file now hashes the tokens and fns of its one parse
(`fn_cache.hash_maps`). These tests count the calls, and pin that the tokens
`module_interface.parse_source_tokens` returns are the lexer's own, unsplit
by the parser, so the hashes (and so the sig files) are unchanged.
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).parent.resolve()
RITZ_DIR = RITZ0_DIR.parent
sys.path.insert(0, str(RITZ0_DIR))

# Generic `>>` closes (the parser splits them) and a pub fn, so both the token
# reuse and the sig hashes are exercised.
SOURCE = textwrap.dedent(
    """\
    import ritzlib.sys

    struct Box<T>
        v: T

    fn inner(b: Box<Box<i32>>) -> i32
        b.v.v >> 1

    pub fn twice(x: i32) -> i32
        x + x

    fn main() -> i32
        let b: Box<Box<i32>> = Box<Box<i32>> { v: Box<i32> { v: 8 } }
        twice(inner(b)) - 8
    """
)

# Runs ritz0's real main() in a fresh interpreter (the emitter keeps
# module-level state, so not in the pytest process) and reports how often
# each path was lexed and parsed.
COUNTER = textwrap.dedent(
    """\
    import collections, json, sys
    sys.path.insert(0, sys.argv[1])
    import lexer, parser
    lexes, parses = collections.Counter(), collections.Counter()
    tokenize, parse_module = lexer.Lexer.tokenize, parser.Parser.parse_module
    def counted_tokenize(self):
        toks = tokenize(self)
        lexes[toks[-1].span.file if toks else "?"] += 1
        return toks
    def counted_parse(self):
        parses[self.tokens[-1].span.file if self.tokens else "?"] += 1
        return parse_module(self)
    lexer.Lexer.tokenize = counted_tokenize
    parser.Parser.parse_module = counted_parse
    import ritz0
    sys.argv = ["ritz0.py", sys.argv[2], "-o", sys.argv[3]]
    try:
        ritz0.main()
    except SystemExit as e:
        if e.code:
            raise
    print(json.dumps({"lexes": lexes, "parses": parses}))
    """
)


@pytest.mark.integration
def test_compile_lexes_and_parses_the_source_once(tmp_path, monkeypatch):
    src = tmp_path / "prog.ritz"
    src.write_text(SOURCE)
    env = dict(
        os.environ, RITZ_PATH=str(RITZ_DIR), RITZ_CACHE_DIR=str(tmp_path / "cache")
    )
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            COUNTER,
            str(RITZ0_DIR),
            str(src),
            str(tmp_path / "prog.ll"),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    counts = json.loads(r.stdout.strip().splitlines()[-1])
    main = str(src)
    assert counts["lexes"].get(main) == 1, counts["lexes"]
    assert counts["parses"].get(main) == 1, counts["parses"]
    # Imports come from their interfaces: lexed at most once (a store miss).
    for path, n in counts["lexes"].items():
        assert n <= 1, (path, n)
    # The fn cache still hashed the source: its sig names the pub fn.
    from emitter import fn_cache

    monkeypatch.setenv("RITZ_CACHE_DIR", env["RITZ_CACHE_DIR"])
    sig = fn_cache.read_sig_file(str(src.resolve()))
    assert sig is not None and "twice" in json.dumps(sig)


@pytest.mark.unit
def test_parse_source_tokens_are_the_lexers_own():
    """The parser splits `>>` in its token list; the returned tokens must not
    be that list, or the fn hashes would change."""
    import module_interface
    from lexer import Lexer

    tokens, module = module_interface.parse_source_tokens(SOURCE, "p.ritz")
    fresh = Lexer(SOURCE, "p.ritz").tokenize()
    assert [(t.type, t.value, t.span.line, t.span.column) for t in tokens] == [
        (t.type, t.value, t.span.line, t.span.column) for t in fresh
    ]
    assert any(getattr(i, "name", None) == "inner" for i in module.items)


@pytest.mark.unit
def test_hash_maps_match_the_old_two_lex_hashes():
    """hash_maps over the one parse == build_hash_map/build_sig_hash_map,
    which lex the source themselves."""
    import module_interface
    from emitter.fn_cache import build_hash_map, build_sig_hash_map, hash_maps

    tokens, module = module_interface.parse_source_tokens(SOURCE, "p.ritz")
    fn_hashes, sig_hashes = hash_maps(tokens, module.items)
    assert fn_hashes == build_hash_map(SOURCE, "p.ritz")
    assert sig_hashes == build_sig_hash_map(SOURCE, "p.ritz")
    assert set(fn_hashes) == {"inner", "twice", "main"}
    assert set(sig_hashes) == {"twice"}
