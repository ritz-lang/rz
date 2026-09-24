"""ritz1's lexer must keep token positions 64-bit — AGAST #1399.

THE DEFECT

`Lexer.pos` is declared i64, and the declaration says why:

    pos: i64                 # Current position (use i64 for large files)

Five token paths in `lexer_next` then threw that away:

    let start: i32 = lex.pos          # truncates
    ...
    tok.start = lex.src + start       # and the truncated value is a pointer offset

So any token more than 2^32 bytes into a file pointed at the wrong byte, with
no diagnostic. The fix widens the locals; it must NOT be `as i32`, which would
silence #1393's narrowing error while keeping the truncation.

HOW THIS TESTS IT WITHOUT A 4 GiB FILE

The lexer only ever reads `*(lex.src + lex.pos)`. So the probe biases `src`
back by 2^32 and starts `pos` at 2^32: every read lands in a small real
buffer, while the position genuinely needs 33 bits. The token's
`start - src` must then be exactly 2^32. A truncating lexer reports 0.

One case per reachable token path, because each path had its own
`let start: i32` and fixing some but not all would otherwise pass as "mostly
green". A mutation run (revert one site, expect exactly its case red) confirms
four of the five sites are individually covered.

The fifth — the hand-written `c"..."` prefix scanner — is widened too but CANNOT
be covered: it is dead for every input that yields a token. It accepts
`c"` (not quote/newline/backslash | backslash-escape)* `"`, a strict subset of
the NFA's own `c"([^"\\]|\\.)*"`, and the NFA takes the longest match; so any
string the fallback could close, the NFA already lexed as TOK_CSTRING. The
`cstring-literal` case below therefore exercises the generic NFA path. The exit code
separates "wrong offset" (the defect, 3) from "wrong token kind" (a broken
probe, 4) — a probe that lexes the wrong thing proves nothing either way.

The probe links ritz1's *real* lexer sources, compiled by ritz0 — this tests
ritz1's source code, not a copy of its shape.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
RITZ1_SRC = RITZ_ROOT / "ritz1" / "src"

# The lexer and everything it transitively imports. ritz0 compiles one module
# at a time, so each is compiled and linked explicitly.
LOCAL_MODULES = ["tokens_gen", "nfa", "regex", "lexer_nfa", "lexer_setup_gen"]
RITZLIB_MODULES = ["memory", "strview", "sys", "str"]

PROBE_HEAD = """\
import tokens_gen
import nfa
import lexer_nfa
import lexer_setup_gen

# Returns start-minus-2^32 (0 when the position survived), or -1 if the lexer
# produced a different token kind than the case expects.
fn probe(buf: *u8, n: i64, want_kind: i32) -> i64
    var nfa_storage: NFA
    var patterns_storage: [128]TokenPattern
    var states_storage: [4096]NFAState
    var trans_storage: [8192]Transition
    var sto_storage: [4096]i64
    var stc_storage: [4096]i64
    var ti_storage:  [8192]i64
    var lex: Lexer
    setup_lexer(@lex, @nfa_storage, @patterns_storage[0], @states_storage[0], @trans_storage[0], @sto_storage[0], @stc_storage[0], @ti_storage[0], 4096, 8192)
    let big: i64 = 4294967296
    let base: *u8 = ((buf as i64) - big) as *u8
    lexer_reset(@lex, base, big + n)
    lex.pos = big
    lex.at_line_start = 0
    var tok: Token = lexer_next(@lex)
    if tok.kind != want_kind
        return -1
    return (tok.start as i64) - (base as i64) - big

fn main() -> i32
    let r: i64 = probe({buf} as *u8, {n}, {kind})
    if r == -1
        return 4
    if r != 0
        return 3
    return 7
"""

# (id, source bytes as a c-string literal, length, expected token kind)
CASES = [
    # lexer_nfa.ritz — the generic NFA-match path, `let start` at the tail
    pytest.param('c"abc "', 4, "TOK_IDENT", id="ident-generic-path"),
    # string literal path: `let start` and the derived `len`
    pytest.param('c"\\"ab\\" "', 5, "TOK_STRING", id="string-literal"),
    # newline token path
    pytest.param('c"\\nx"', 2, "TOK_NEWLINE", id="newline"),
    # c"..." literal — lexed by the NFA pattern, i.e. the generic path again
    pytest.param('c"c\\"ab\\" "', 6, "TOK_CSTRING", id="cstring-literal"),
    # no pattern matches -> single-char error token path
    pytest.param('c"` "', 2, "TOK_ERROR", id="error-token"),
]


def _ritz0(src: Path, out: Path, *extra: str) -> None:
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [sys.executable, str(RITZ0), str(src), "-o", str(out), *extra],
        cwd=src.parent, capture_output=True, text=True, env=env, timeout=600,
    )
    assert proc.returncode == 0, (
        f"ritz0 failed on {src.name}:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    )


@pytest.fixture(scope="module")
def lexer_objects(tmp_path_factory) -> tuple[Path, list[Path]]:
    """Compile ritz1's lexer modules once; return (workdir, [.ll files])."""
    work = tmp_path_factory.mktemp("ritz1_lexer")
    # Imports resolve from the importing file's directory, so the probe must
    # sit beside the lexer sources. Link them in rather than copying, so the
    # test can never drift from the real files.
    for f in RITZ1_SRC.glob("*.ritz"):
        if f.name != "main.ritz":
            (work / f.name).symlink_to(f)
    lls = []
    for m in LOCAL_MODULES:
        out = work / f"{m}.ll"
        _ritz0(work / f"{m}.ritz", out, "--no-runtime")
        lls.append(out)
    for m in RITZLIB_MODULES:
        out = work / f"lib_{m}.ll"
        _ritz0(RITZ_ROOT / "ritzlib" / f"{m}.ritz", out, "--no-runtime")
        lls.append(out)
    return work, lls


@pytest.mark.parametrize("buf,n,kind", CASES)
def test_token_start_survives_a_position_past_4gib(lexer_objects, buf, n, kind, request):
    work, lls = lexer_objects
    # Keyed on the case id, not the token kind: two cases share TOK_CSTRING.
    case = work / f"probe_{request.node.callspec.id}"
    case.mkdir()
    for f in work.glob("*.ritz"):
        (case / f.name).symlink_to(f.resolve())
    probe = case / "probe.ritz"
    probe.write_text(PROBE_HEAD.format(buf=buf, n=n, kind=kind))
    probe_ll = case / "probe.ll"
    _ritz0(probe, probe_ll)

    exe = case / "probe"
    link = subprocess.run(
        ["clang", "-O0", "-nostdlib", "-static", "-Wno-override-module",
         str(probe_ll), *map(str, lls), "-o", str(exe)],
        capture_output=True, text=True, timeout=300,
    )
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"

    rc = subprocess.run([str(exe)], timeout=60).returncode
    assert rc != 4, (
        f"probe lexed the wrong token kind (wanted {kind}) — the probe is "
        "broken, so this case proves nothing"
    )
    assert rc != 3, (
        f"{kind} token 2^32 bytes into the source got the wrong start offset — "
        "the lexer truncated its i64 position (#1399)"
    )
    assert rc == 7, f"unexpected exit {rc}"
