"""AGAST #1368: ritz1 resolves method calls on non-generic ritzlib types
through the same type -> function-prefix table as ritz0.

THE DEFECT

ritzlib's String / Buffer / ArgParser "methods" are free functions with a
prefix that is NOT always the lowercased type name:

    String    -> string_       (string_push_str)
    GrowBuf   -> growbuf_
    Buffer    -> buf_          (.lower() would give buffer_   -- wrong)
    ArgParser -> args_         (.lower() would give argparser_ -- wrong)

ritz0 reaches them through `_find_method_fallback`. ritz1 had the generic
half of that table (Vec$ -> vec_, Span$ -> span_) but not the non-generic
half, so `s.push_str("hi")` fell through to the verbatim `Type_method`
mangling: it forward-declared `@String_push_str`, a symbol nothing defines,
and failed at LINK time with no source location.

MEASURED (ritz1 before/after, 84 examples/ entry files, symbols matching
`@(String|Buffer|ArgParser|GrowBuf)_*` in the emitted IR):

    before @ 031cb04:
      tier5_async/50_http       String_push_cstr, String_push_i64, String_push_str
      tier5_async/51_loadtest   String_push_str, String_push_string
    after: none (both now call string_*). The same 17 entries fail to compile
    before and after, so they are unmeasured; nothing regressed.

THE TESTS

  * runtime cases (ritz0 is the oracle): String, Buffer and ArgParser method
    calls -- on a local, through a pointer parameter, and through a struct
    field -- build, link and compute the right answer; Vec$u8.len() still
    does (generic-table coverage).
  * a user `impl` method wins over the table: a program defining its own
    `impl Buffer` with `len` AND a free `buf_len` gets the impl method.
  * IR: for the ticket's repro ritz0 and ritz1 call the same symbols, and
    ritz1 declares no `@String_*`.
  * the ritz1 table and ritz0's table list the same pairs, so the two copies
    cannot drift silently (they already live in two languages).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import (  # noqa: F401
    RITZ0,
    RITZ1_BIN,
    RITZ_ROOT,
    _run_pkg,
    ritz1_bin,
)

import emitter_llvmlite

RITZ1_CALL_SRC = RITZ_ROOT / "ritz1" / "src" / "emitter_expr_call.ritz"

# The ticket's repro, on the post-#1474 API (push_str takes a StrView).
REPRO = """\
import ritzlib.string
import ritzlib.io

fn main() -> i32
    var s: String = string_new()
    s.push_str("hi")
    return s.len() as i32
"""

# Every String method shape: StrView / *u8 / @String / u8 args, i64 / i32 /
# bool returns.
STRING_METHODS = """\
import ritzlib.string

fn main() -> i32
    var s: String = string_new()
    var t: String = string_new()
    s.push_str("ab")
    s.push_cstr(c"cd")
    s.push('e')
    t.push_str("XY")
    s.push_string(@t)
    if s.len() != 7
        return 1
    if s.eq("abcdeXY") == false
        return 2
    if s.eq("abcde") == true
        return 3
    if s.starts_with("abc") != 1
        return 4
    if s.contains("eX") != 1
        return 5
    return 42
"""

# Receiver is a pointer parameter (ptr-of-ptr slot) and a struct field.
STRING_RECEIVER_KINDS = """\
import ritzlib.string

struct Req
    tag: i64
    body: String

fn fill(out: @&String) -> i64
    out.push_str("GET ")
    out.push_cstr(c"/x")
    return out.len()

fn main() -> i32
    var s: String = string_new()
    let n: i64 = fill(@&s)
    var r: Req
    r.tag = 1
    r.body = string_new()
    r.body.push_str("abc")
    if n != 6
        return 1
    if s.len() != 6
        return 2
    if r.body.len() != 3
        return 3
    return 42
"""

# Buffer -> buf_ : the first entry that disproves the .lower() rule.
BUFFER_METHODS = """\
import ritzlib.buf

fn main() -> i32
    var b: Buffer
    b.init(c"hello", 5)
    let h: u8 = b.advance()
    if h != 'h'
        return 1
    if b.peek() != 'e'
        return 2
    if b.remaining() != 4
        return 3
    if b.len() != 5
        return 4
    return 42
"""

# ArgParser -> args_ : the second entry that disproves the .lower() rule.
ARGPARSER_METHODS = """\
import ritzlib.args

fn main() -> i32
    var p: ArgParser
    p.init(c"prog", c"test")
    p.flag('v', c"verbose", c"be loud")
    if p.get_flag('v') != 0
        return 1
    return 42
"""

# Generic half of the table: Vec$u8.len() and a vec_ method.
VEC_METHODS = """\
import ritzlib.gvec

fn main() -> i32
    var v: Vec<u8> = vec_new<u8>()
    v.push(7)
    v.push(9)
    if v.len() != 2
        return 1
    return 42
"""

# A user impl method beats the table, even with a matching free function.
IMPL_WINS = """\
struct Buffer
    n: i64

impl Buffer
    fn len(self: @Buffer) -> i64
        return 7

fn buf_len(b: @Buffer) -> i64
    return 99

fn main() -> i32
    var b: Buffer
    b.n = 0
    return b.len() as i32
"""

CASES = {
    "repro": (REPRO, 2),
    "string_methods": (STRING_METHODS, 42),
    "string_receiver_kinds": (STRING_RECEIVER_KINDS, 42),
    "buffer_methods": (BUFFER_METHODS, 42),
    "argparser_methods": (ARGPARSER_METHODS, 42),
    "vec_methods": (VEC_METHODS, 42),
    "impl_wins": (IMPL_WINS, 7),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_ufcs_prefix(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want


_CALL_RE = re.compile(r"call [^@]*@\"?([A-Za-z_][\w$.]*)\"?\(")


def _called_symbols(compiler: str, tmp_path: Path) -> set:
    src = tmp_path / f"repro_{compiler}.ritz"
    src.write_text(REPRO)
    ll = tmp_path / f"repro_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    proc = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    text = ll.read_text()
    # Only main's body: ritz0 also emits ritzlib bodies into the module.
    m = re.search(r'define [^\n]*@"?main"?\(', text)
    assert m, "no main in IR"
    body = text[m.end() :].split("\n}", 1)[0]
    return set(_CALL_RE.findall(body)), text


@pytest.mark.integration
def test_repro_calls_same_symbols_as_ritz0(ritz1_bin, tmp_path):  # noqa: F811
    r0, _ = _called_symbols("ritz0", tmp_path)
    r1, r1_text = _called_symbols("ritz1", tmp_path)
    want = {"string_new", "string_push_str", "string_len"}
    assert want <= r0, r0
    assert want <= r1, r1
    assert "@String_" not in r1_text, [
        ln for ln in r1_text.splitlines() if "@String_" in ln
    ]


# Delimits ritz1's table so this test can read it without a Ritz parser.
_R1_BEGIN = "# BEGIN UFCS_NON_GENERIC_PREFIXES"
_R1_END = "# END UFCS_NON_GENERIC_PREFIXES"
_R1_PAIR_RE = re.compile(r'c"([A-Za-z_]\w*)",\s*\d+,\s*c"([a-z_]+)",\s*\d+')


def _ritz1_table() -> dict:
    src = RITZ1_CALL_SRC.read_text()
    assert _R1_BEGIN in src and _R1_END in src, "ritz1 prefix table markers missing"
    block = src.split(_R1_BEGIN, 1)[1].split(_R1_END, 1)[0]
    pairs = _R1_PAIR_RE.findall(block)
    # The literal lengths passed alongside each c"..." must be right.
    for m in re.finditer(r'c"(\w+)",\s*(\d+)', block):
        assert len(m.group(1)) == int(m.group(2)), m.group(0)
    return dict(pairs)


@pytest.mark.unit
def test_prefix_tables_agree():
    r1 = _ritz1_table()
    r0 = dict(emitter_llvmlite.UFCS_NON_GENERIC_PREFIXES)
    assert r1 == r0
    # The two entries that disprove the .lower() rule must be present.
    assert r0["Buffer"] == "buf_"
    assert r0["ArgParser"] == "args_"
