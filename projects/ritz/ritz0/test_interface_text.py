"""Module interfaces as Ritz source text (G9c, AGAST #1901).

ritz0 stores each module's interface as Ritz source -- the module with every
stripped fn turned into a declaration-only `fn ... = extern` (#1900) and its
body lines emptied -- under a key of the source bytes alone
(module_interface.text_key). ritz1 looks it up and parses it instead of the
import's source (ritz1/src/main.ritz load_and_parse).

Contract tested here:
  - the text's shape: headers kept, bodies emptied, every line and column of
    what is kept is the source's, [[test]]/generic/async/trait kept verbatim;
  - parsing the text gives the stripped module, spans included, across the
    whole ritzlib + ritz1 corpus;
  - the store layout and key, which ritz1 recomputes (sha256 in ritz1/src);
  - ritz1 reads it: a warm compile parses only main, and its IR is the same
    as a compile that parsed every import.
"""

from __future__ import annotations

import copy
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_DIR = RITZ0_DIR.parent
sys.path.insert(0, str(RITZ0_DIR))
sys.path.insert(0, str(RITZ_DIR))

import module_interface as mi  # noqa: E402
import ritz_ast as rast  # noqa: E402
from lexer import Lexer  # noqa: E402
from parser import Parser  # noqa: E402

from test_module_interface import LIB, MAIN  # noqa: E402

RITZ1_BUILD = RITZ_DIR / "ritz1" / "build"


@pytest.fixture
def store(tmp_path, monkeypatch):
    root = tmp_path / "cas"
    monkeypatch.setenv("RITZ_CACHE_DIR", str(root))
    monkeypatch.delenv(mi.DISABLE_ENV, raising=False)
    mi.PARSED.clear()
    mi._HASH_MEMO.clear()
    return root


@pytest.fixture
def proj(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    (d / "lib.ritz").write_text(LIB)
    (d / "main.ritz").write_text(MAIN)
    return d


def _text(source: str) -> str:
    tokens, module = mi._parse_with_tokens(source, "t.ritz")
    return mi.interface_text(source, tokens, module)


def _text_path(store: Path, source_bytes: bytes) -> Path:
    k = mi.text_key(source_bytes)
    return store / "objects" / k[:2] / f"{k}.{mi.TEXT_EXT}"


# ---------------------------------------------------------------------------
# The text
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestShape:
    def test_lines_preserved(self):
        assert _text(LIB).count("\n") == LIB.count("\n")

    def test_plain_fn_declared_body_emptied(self):
        lines = _text(LIB).split("\n")
        i = lines.index("pub fn plain(x: i64) -> i64 = extern")
        assert lines[i + 1:i + 3] == ["", ""]

    def test_plain_impl_method_declared(self):
        lines = _text(LIB).split("\n")
        i = lines.index("    pub fn sum(self: *Pair) -> i64 = extern")
        assert lines[i + 1] == ""

    def test_generic_fn_and_generic_impl_kept(self):
        text = _text(LIB)
        assert "pub fn ident<T>(x: T) -> T\n    x\n" in text
        assert "    pub fn get(self: *Wrap<T>) -> T\n        self.v\n" in text

    def test_everything_else_verbatim(self):
        src = LIB
        text = _text(src)
        for a, b in zip(src.split("\n"), text.split("\n")):
            assert b == a or b == "" or b.endswith(" = extern"), (a, b)

    @pytest.mark.parametrize("src", [
        "[[test]]\nfn test_x() -> i32\n    0\n",
        "async fn go() -> i32\n    1\n",
        "trait T\n    fn f(self: *Self) -> i32\n",
        "extern fn write(fd: i32, p: *u8, n: i64) -> i64\n",
        "pub fn d(x: i32) -> i32 = extern\n",
        "const C: i32 = 3\n\nstruct S\n    x: i32\n",
    ])
    def test_kept_verbatim(self, src):
        assert _text(src) == src

    def test_bracketed_header(self):
        """Parens/brackets in params and return type; no multi-line form
        exists (the lexer has no bracket continuation)."""
        src = "fn f(cb: fn(i32) -> i32, a: *[4]i32) -> *[2]i32\n    a as *[2]i32\n"
        assert _text(src) == "fn f(cb: fn(i32) -> i32, a: *[4]i32) -> *[2]i32 = extern\n\n"

    def test_header_comment_dropped(self):
        src = "fn f() -> i32  # the answer\n    42\n"
        assert _text(src) == "fn f() -> i32 = extern\n\n"

    def test_attribute_on_header_line(self):
        src = "[[inline]] pub fn f() -> i32\n    42\n"
        assert _text(src) == "[[inline]] pub fn f() -> i32 = extern\n\n"

    def test_body_comments_and_blank_lines(self):
        """Blank and comment-only lines -- even at column 0 -- don't end a
        body; comment lines after its last code line are not the body's."""
        src = ("fn f() -> i32\n    let x: i32 = 1\n\n# col-0 note\n    x\n"
               "# about g\n\nfn g() -> i32\n    2\n")
        assert _text(src) == ("fn f() -> i32 = extern\n\n\n\n\n"
                              "# about g\n\nfn g() -> i32 = extern\n\n")

    def test_no_trailing_newline(self):
        assert _text("fn f() -> i32\n    1") == "fn f() -> i32 = extern\n"


def _norm(module: rast.Module) -> list:
    """Canonical items, spans included; bodyless fns compared as stripped."""
    def fix(fn):
        if fn.body.stmts or fn.body.expr is not None:
            return fn
        fn = copy.copy(fn)
        fn.body = rast.Block(None, [], None)
        fn.is_decl = False
        return fn
    out = []
    for item in mi.strip_module(module).items:
        if isinstance(item, rast.FnDef):
            item = fix(item)
        elif isinstance(item, rast.ImplBlock):
            item = copy.copy(item)
            item.methods = [fix(m) for m in item.methods]
        toks: list = []
        mi._canon(item, toks, keep_spans=True)
        out.append("\x00".join(toks))
    return out


CORPUS = sorted([*(RITZ_DIR / "ritzlib").rglob("*.ritz"),
                 *(RITZ_DIR / "ritz1" / "src").glob("*.ritz")])


@pytest.mark.unit
def test_text_parses_to_stripped_module_across_corpus():
    """The interface text of every corpus module parses to its stripped
    module, every span the same: a reader sees what ritz0's interface is."""
    checked = 0
    for path in CORPUS:
        src = path.read_text()
        try:
            tokens, module = mi._parse_with_tokens(src, str(path))
        except Exception:
            continue  # doesn't parse in ritz0 (fixtures of error tests)
        text = mi.interface_text(src, tokens, module)
        assert text.count("\n") == src.count("\n"), path
        again = Parser(Lexer(text, str(path)).tokenize()).parse_module()
        assert _norm(again) == _norm(module), path
        checked += 1
    assert checked > 50


# ---------------------------------------------------------------------------
# The store
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestStore:
    def test_key_formula(self):
        """The language-neutral key ritz1 recomputes (main.ritz iface_text_path)."""
        src = b"fn f() -> i32\n    1\n"
        inner = hashlib.sha256(src).hexdigest()
        want = hashlib.sha256(f"ritz-iface-text-v1\n{inner}".encode()).hexdigest()
        assert mi.TEXT_SCHEMA == "ritz-iface-text-v1"
        assert mi.text_key(src) == want

    def test_interface_hash_writes_text(self, proj, store):
        lib = proj / "lib.ritz"
        mi.interface_hash(str(lib))
        p = _text_path(store, lib.read_bytes())
        assert p.read_text() == _text(LIB)

    def test_load_interface_writes_text(self, proj, store):
        lib = proj / "lib.ritz"
        mi.load_interface(str(lib))
        assert _text_path(store, lib.read_bytes()).is_file()

    def test_key_has_no_path(self, tmp_path, store):
        """Two copies of one source share one text: no path in the key."""
        for d in ("a", "b"):
            (tmp_path / d).mkdir()
            (tmp_path / d / "lib.ritz").write_text(LIB)
            mi.interface_hash(str(tmp_path / d / "lib.ritz"))
        assert len(list(store.rglob(f"*.{mi.TEXT_EXT}"))) == 1

    def test_store_without_text_is_completed(self, proj, store):
        """A store from before #1901 (pickle and hash, no text) gains it."""
        lib = proj / "lib.ritz"
        mi.interface_hash(str(lib))
        p = _text_path(store, lib.read_bytes())
        p.unlink()
        mi._HASH_MEMO.clear()
        mi.interface_hash(str(lib))
        assert p.is_file()
        p.unlink()
        mi.load_interface(str(lib))
        assert p.is_file()


# ---------------------------------------------------------------------------
# ritz1 reads it
# ---------------------------------------------------------------------------

@pytest.fixture(params=["ritz1", "ritz1_selfhosted"])
def compiler(request, ritz1_bin, monkeypatch):
    """Both ritz1 binaries: the selfhosted one runs sha256 as ritz1 compiled it."""
    binary = RITZ1_BUILD / request.param
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    monkeypatch.setattr(sys.modules[__name__], "_BIN", binary)
    return request.param


_BIN = RITZ1_BUILD / "ritz1"


def _ritz1(main: Path, out: Path, store: Path, log: Path = None) -> None:
    env = dict(os.environ, RITZ_PATH=str(RITZ_DIR), RITZ_CACHE_DIR=str(store))
    env.pop("RITZ1_PARSE_LOG", None)
    if log is not None:
        env["RITZ1_PARSE_LOG"] = str(log)
    r = subprocess.run([str(_BIN), str(main), "-o", str(out)],
                       capture_output=True, text=True, cwd=str(main.parent),
                       env=env, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Skipped (unchanged)" not in r.stdout  # a real compile


def _parsed(log: Path) -> list:
    return log.read_text().split() if log.exists() else []


def _warm(paths, store: Path, monkeypatch) -> None:
    """Store the interface texts of `paths`, as build.py's keying does."""
    monkeypatch.setenv("RITZ_CACHE_DIR", str(store))
    mi._HASH_MEMO.clear()
    for p in paths:
        mi.interface_hash(str(p))


@pytest.mark.integration
@pytest.mark.usefixtures("compiler")  # conftest session build (#1804); fails, never skips
class TestRitz1:
    def test_cold_compile_parses_import(self, proj, tmp_path):
        log = tmp_path / "parse.log"
        _ritz1(proj / "main.ritz", tmp_path / "m.ll", tmp_path / "empty", log)
        assert _parsed(log) == [str(proj / "main.ritz"), str(proj / "lib.ritz")]

    def test_warm_compile_parses_only_main(self, proj, tmp_path, monkeypatch):
        store = tmp_path / "warm"
        _warm([proj / "lib.ritz"], store, monkeypatch)
        log = tmp_path / "parse.log"
        _ritz1(proj / "main.ritz", tmp_path / "m.ll", store, log)
        assert _parsed(log) == [str(proj / "main.ritz")]

    def test_ir_identical_to_full_parse(self, proj, tmp_path, monkeypatch):
        store = tmp_path / "warm"
        _warm([proj / "lib.ritz"], store, monkeypatch)
        _ritz1(proj / "main.ritz", tmp_path / "warm.ll", store)
        _ritz1(proj / "main.ritz", tmp_path / "cold.ll", tmp_path / "empty")
        assert (tmp_path / "warm.ll").read_text() == (tmp_path / "cold.ll").read_text()

    def test_reads_the_stored_text(self, proj, tmp_path, monkeypatch):
        """What ritz1 parses is the stored text: a struct field only it
        holds reaches the IR (so a hit is not a silent full parse)."""
        store = tmp_path / "warm"
        lib = proj / "lib.ritz"
        _warm([lib], store, monkeypatch)
        p = _text_path(store, lib.read_bytes())
        text = p.read_text()
        assert "    b: i64\n" in text
        p.write_text(text.replace("    b: i64\n", "    b: i64\n    only_in_iface: i8\n", 1))
        _ritz1(proj / "main.ritz", tmp_path / "m.ll", store)
        ir = (tmp_path / "m.ll").read_text()
        assert re.search(r"^%Pair = type \{\s*i64, i64, i8\s*\}", ir, re.M), \
            [ln for ln in ir.splitlines() if ln.startswith("%Pair")]

    # Source lengths around SHA-256's padding boundaries (ritz1/src/sha256.ritz
    # must agree with hashlib for every tail length class).
    @pytest.mark.parametrize("rem", [0, 1, 55, 56, 63])
    def test_key_agrees_at_padding_boundaries(self, proj, tmp_path, monkeypatch, rem):
        lib = proj / "lib.ritz"
        base = LIB + "# pad"
        pad = (rem - len(base.encode()) - 1) % 64
        lib.write_text(base + "x" * pad + "\n")
        assert len(lib.read_bytes()) % 64 == rem
        store = tmp_path / "warm"
        _warm([lib], store, monkeypatch)
        log = tmp_path / "parse.log"
        _ritz1(proj / "main.ritz", tmp_path / "m.ll", store, log)
        assert _parsed(log) == [str(proj / "main.ritz")]

    def test_ritz1_closure_ir_identical(self, tmp_path, monkeypatch):
        """A real closure: ritz1's own main.ritz and every module it imports,
        warm (all interface texts stored) vs cold."""
        from import_resolver import collect_all_source_files
        main = RITZ_DIR / "ritz1" / "src" / "main.ritz"
        monkeypatch.setenv("RITZ_PATH", str(RITZ_DIR))
        closure = [Path(p) for p in collect_all_source_files(str(main))
                   if Path(p).resolve() != main.resolve()]
        assert len(closure) > 20
        store = tmp_path / "warm"
        _warm(closure, store, monkeypatch)
        log = tmp_path / "parse.log"
        _ritz1(main, tmp_path / "warm.ll", store, log)
        assert _parsed(log) == [str(main)]
        _ritz1(main, tmp_path / "cold.ll", tmp_path / "empty")
        assert (tmp_path / "warm.ll").read_text() == (tmp_path / "cold.ll").read_text()
