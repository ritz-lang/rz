#!/usr/bin/env python3
"""G9 separate compilation via module interfaces (AGAST #1810).

ritz0 used to lex, parse and merge the *entire* transitive import closure on
every invocation (``ImportResolver(use_cache=False)``), so one gate parsed
``ritzlib/sys.ritz`` thousands of times. Now each imported module is loaded
as an *interface*: the parsed module with the bodies it does not export
stripped, stored in the G7 artifact store (``cas.py``) keyed by the module's
path, source bytes and the parser's fingerprint.

What the interface keeps, and why:

* every item except non-generic function bodies: structs, enums, consts,
  type aliases, traits (default methods), vars, externs, static asserts and
  imports (``pub import`` re-exports, aliases);
* bodies of generic fns, async fns and methods of generic impls -- the
  importer monomorphises / state-machine-transforms them and emits them
  locally, so it needs the body.

The *interface hash* is what an importer's artifact key depends on. It
ignores source positions outside kept bodies, so a body-only edit -- even
one that shifts every later line -- leaves dependents' keys unchanged.
"""

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


LIB = """\
pub struct Pair
    a: i64
    b: i64

pub const LIMIT: i64 = 42

pub fn plain(x: i64) -> i64
    let y: i64 = x + 1
    y * 2

pub fn ident<T>(x: T) -> T
    x

pub struct Wrap<T>
    v: T

impl<T> Wrap<T>
    pub fn get(self: *Wrap<T>) -> T
        self.v

impl Pair
    pub fn sum(self: *Pair) -> i64
        self.a + self.b
"""

MAIN = """\
import lib

fn main() -> i32
    let p: Pair = Pair { a: 1, b: 2 }
    let w: Wrap<i64> = Wrap<i64> { v: plain(LIMIT) }
    let s: i64 = p.sum() + ident<i64>(w.get())
    (s - s) as i32
"""


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A private artifact store; parse log reset per test."""
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


def _fns(module):
    return {i.name: i for i in module.items if isinstance(i, rast.FnDef)}


def _impls(module):
    return [i for i in module.items if isinstance(i, rast.ImplBlock)]


# ---------------------------------------------------------------------------
# What an interface contains
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestStrip:
    def test_non_generic_fn_body_stripped(self, proj, store):
        iface = mi.load_interface(str(proj / "lib.ritz"))
        plain = _fns(iface)["plain"]
        assert plain.body.stmts == [] and plain.body.expr is None
        # Signature survives.
        assert [p.name for p in plain.params] == ["x"]
        assert plain.ret_type is not None and plain.is_pub

    def test_generic_fn_body_kept(self, proj, store):
        iface = mi.load_interface(str(proj / "lib.ritz"))
        assert _fns(iface)["ident"].body.expr is not None

    def test_generic_impl_methods_kept_plain_impl_stripped(self, proj, store):
        iface = mi.load_interface(str(proj / "lib.ritz"))
        by_type = {i.type_name: i for i in _impls(iface)}
        assert by_type["Wrap"].methods[0].body.expr is not None
        assert by_type["Pair"].methods[0].body.expr is None

    def test_async_fn_body_kept(self, tmp_path, store):
        src = tmp_path / "a.ritz"
        src.write_text("pub async fn f(x: i32) -> i32\n    x + 1\n")
        f = _fns(mi.load_interface(str(src)))["f"]
        assert f.body.expr is not None

    def test_non_fn_items_and_imports_kept(self, tmp_path, store):
        (tmp_path / "dep.ritz").write_text("pub const K: i32 = 1\n")
        src = tmp_path / "m.ritz"
        src.write_text("pub import dep\n\npub struct S\n    x: i32\n\n"
                       "pub const C: i32 = 3\n")
        iface = mi.load_interface(str(src))
        kinds = [type(i).__name__ for i in iface.items]
        assert kinds == ["Import", "StructDef", "ConstDef"]
        assert iface.items[0].is_pub

    def test_original_module_not_mutated(self, proj):
        mod = mi.parse_source(LIB, str(proj / "lib.ritz"))
        mi.strip_module(mod)
        assert _fns(mod)["plain"].body.expr is not None


# ---------------------------------------------------------------------------
# Storage: parse once per (path, content, parser)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestStore:
    def test_second_load_does_not_parse(self, proj, store):
        lib = str(proj / "lib.ritz")
        mi.load_interface(lib)
        assert mi.PARSED == [lib]
        mi.PARSED.clear()
        iface = mi.load_interface(lib)
        assert mi.PARSED == []
        assert "plain" in _fns(iface)

    def test_source_edit_reparses(self, proj, store):
        lib = proj / "lib.ritz"
        mi.load_interface(str(lib))
        lib.write_text(LIB.replace("LIMIT: i64 = 42", "LIMIT: i64 = 43"))
        mi.PARSED.clear()
        iface = mi.load_interface(str(lib))
        assert mi.PARSED == [str(lib)]
        const = [i for i in iface.items if isinstance(i, rast.ConstDef)][0]
        assert const.value.value == 43

    def test_corrupt_entry_is_rebuilt(self, proj, store):
        lib = str(proj / "lib.ritz")
        mi.load_interface(lib)
        for p in store.rglob(f"*.{mi.IFACE_EXT}"):
            p.write_bytes(b"torn")
        mi.PARSED.clear()
        assert "plain" in _fns(mi.load_interface(lib))
        assert mi.PARSED == [lib]

    def test_unwritable_store_still_loads(self, proj, tmp_path, monkeypatch):
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("")
        monkeypatch.setenv("RITZ_CACHE_DIR", str(blocker / "cas"))
        iface = mi.load_interface(str(proj / "lib.ritz"))
        assert "plain" in _fns(iface)

    def test_disabled_parses_full_module(self, proj, store, monkeypatch):
        monkeypatch.setenv(mi.DISABLE_ENV, "1")
        assert not mi.enabled()

    def test_parse_log_env(self, proj, store, tmp_path, monkeypatch):
        log = tmp_path / "parses.log"
        monkeypatch.setenv(mi.PARSE_LOG_ENV, str(log))
        mi.parse_source(LIB, str(proj / "lib.ritz"))
        assert log.read_text().splitlines() == [str(proj / "lib.ritz")]


# ---------------------------------------------------------------------------
# Interface hash: what invalidates importers
# ---------------------------------------------------------------------------

def _hash_of(path: Path, text: str) -> str:
    path.write_text(text)
    mi._HASH_MEMO.clear()
    return mi.interface_hash(str(path))


@pytest.mark.unit
class TestInterfaceHash:
    def test_body_only_edit_same_hash(self, proj, store):
        lib = proj / "lib.ritz"
        h0 = _hash_of(lib, LIB)
        assert _hash_of(lib, LIB.replace("y * 2", "y * 3")) == h0

    def test_line_shifting_body_edit_same_hash(self, proj, store):
        """Added lines in a stripped body move every later item's span."""
        lib = proj / "lib.ritz"
        h0 = _hash_of(lib, LIB)
        shifted = LIB.replace("    y * 2\n", "    let z: i64 = y\n\n    z * 2\n")
        # ...but the generic items below `plain` keep their bodies and so
        # their positions (debug info of the importer's instantiation).
        # Move `plain` last so nothing kept sits below the edit.
        tail_plain = (LIB.replace(
            "pub fn plain(x: i64) -> i64\n    let y: i64 = x + 1\n    y * 2\n\n", "")
            + "\npub fn plain(x: i64) -> i64\n    let y: i64 = x + 1\n    y * 2\n")
        h1 = _hash_of(lib, tail_plain)
        assert _hash_of(lib, tail_plain.replace(
            "    y * 2\n", "    let z: i64 = y\n\n    z * 2\n")) == h1
        assert _hash_of(lib, shifted) != h0  # kept generic bodies moved

    def test_shift_moves_only_stripped_items_same_hash(self, tmp_path, store):
        """Declarations below a grown body move, but never reach the importer."""
        src = tmp_path / "m.ritz"
        text = ("pub fn a(x: i64) -> i64\n    x\n\n"
                "pub fn b(x: i64) -> i64\n    x\n\n"
                "pub struct S\n    v: i64\n\npub const C: i64 = 1\n")
        h0 = _hash_of(src, text)
        grown = text.replace("    x\n\npub fn b", "    let y: i64 = x\n\n\n    y\n\npub fn b")
        assert _hash_of(src, grown) == h0

    def test_signature_change_changes_hash(self, proj, store):
        lib = proj / "lib.ritz"
        h0 = _hash_of(lib, LIB)
        assert _hash_of(lib, LIB.replace("plain(x: i64) -> i64",
                                         "plain(x: i32) -> i64")) != h0

    def test_struct_layout_change_changes_hash(self, proj, store):
        lib = proj / "lib.ritz"
        h0 = _hash_of(lib, LIB)
        assert _hash_of(lib, LIB.replace("    b: i64\n", "    b: i32\n", 1)) != h0

    def test_const_change_changes_hash(self, proj, store):
        lib = proj / "lib.ritz"
        h0 = _hash_of(lib, LIB)
        assert _hash_of(lib, LIB.replace("= 42", "= 41")) != h0

    def test_generic_body_change_changes_hash(self, proj, store):
        lib = proj / "lib.ritz"
        h0 = _hash_of(lib, LIB)
        assert _hash_of(lib, LIB.replace("pub fn ident<T>(x: T) -> T\n    x\n",
                                         "pub fn ident<T>(x: T) -> T\n    let y: T = x\n    y\n")) != h0

    def test_hash_stable_across_processes(self, proj, store):
        """No set/hash-seed ordering may leak into the digest."""
        code = ("import sys; sys.path[:0] = [%r, %r]; import module_interface as mi; "
                "print(mi.interface_hash(%r))" % (str(RITZ0_DIR), str(RITZ_DIR),
                                                   str(proj / "lib.ritz")))
        outs = set()
        for seed in ("1", "2"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            outs.add(subprocess.run([sys.executable, "-c", code], env=env,
                                    capture_output=True, text=True,
                                    check=True).stdout.strip())
        assert len(outs) == 1


# ---------------------------------------------------------------------------
# The compiler: one module parsed per compile, identical IR
# ---------------------------------------------------------------------------

def _ritz0(main: Path, out: Path, env_extra=None) -> subprocess.CompletedProcess:
    env = dict(os.environ, **(env_extra or {}))
    r = subprocess.run([sys.executable, str(RITZ0_DIR / "ritz0.py"), str(main),
                        "-o", str(out), "--no-runtime"],
                       capture_output=True, text=True, cwd=str(main.parent), env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


@pytest.mark.integration
class TestCompiler:
    def test_warm_compile_parses_only_main(self, proj, store, tmp_path):
        log = tmp_path / "parses.log"
        main = proj / "main.ritz"
        env = {mi.PARSE_LOG_ENV: str(log)}
        _ritz0(main, tmp_path / "a.ll", env)
        cold = log.read_text().splitlines()
        assert sorted(cold) == sorted([str(main), str(proj / "lib.ritz")])
        log.unlink()
        # A different output path defeats ritz0's own "unchanged" fast path.
        _ritz0(main, tmp_path / "b.ll", env)
        assert log.read_text().splitlines() == [str(main)]

    def test_ir_identical_to_full_parse(self, proj, store, tmp_path):
        main = proj / "main.ritz"
        _ritz0(main, tmp_path / "iface.ll")
        _ritz0(main, tmp_path / "full.ll", {mi.DISABLE_ENV: "1"})
        assert (tmp_path / "iface.ll").read_text() == (tmp_path / "full.ll").read_text()


# ---------------------------------------------------------------------------
# build.py: importers' artifact keys follow interface hashes (ritz0 only)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildKey:
    def _key(self, proj, compiler):
        import build
        cache = build.get_build_cache(compiler)
        cache.set_import_context(project_root=proj)
        return build.cas_module_key(proj / "main.ritz", cache, compiler)

    def test_body_only_edit_keeps_ritz0_importer_key(self, proj, store):
        k0 = self._key(proj, "ritz0")
        assert k0
        (proj / "lib.ritz").write_text(LIB.replace("y * 2", "y * 5"))
        mi._HASH_MEMO.clear()
        assert self._key(proj, "ritz0") == k0

    def test_signature_edit_changes_ritz0_importer_key(self, proj, store):
        k0 = self._key(proj, "ritz0")
        (proj / "lib.ritz").write_text(LIB.replace("plain(x: i64)", "plain(x: i32)"))
        mi._HASH_MEMO.clear()
        assert self._key(proj, "ritz0") != k0

    # G9b (AGAST #1899): ritz1 strips its imports to their interfaces
    # (TestRitz1Compiler), so its objects follow interface hashes too.
    @pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
    def test_body_only_edit_keeps_ritz1_importer_key(self, proj, store, compiler):
        k0 = self._key(proj, compiler)
        assert k0
        (proj / "lib.ritz").write_text(LIB.replace("y * 2", "y * 5"))
        mi._HASH_MEMO.clear()
        assert self._key(proj, compiler) == k0

    @pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
    def test_signature_edit_changes_ritz1_importer_key(self, proj, store, compiler):
        k0 = self._key(proj, compiler)
        (proj / "lib.ritz").write_text(LIB.replace("plain(x: i64)", "plain(x: i32)"))
        mi._HASH_MEMO.clear()
        assert self._key(proj, compiler) != k0

    def test_compilers_keep_distinct_keys(self, proj, store):
        """Same deps digest, but ritz0 and ritz1 objects must never collide."""
        assert self._key(proj, "ritz0") != self._key(proj, "ritz1")


# ---------------------------------------------------------------------------
# ritz1 (G9b, AGAST #1899): an importer's IR depends only on its imports'
# interfaces -- the precondition for keying ritz1 objects on interface hashes
# ---------------------------------------------------------------------------

RITZ1_BIN = RITZ_DIR / "ritz1" / "build" / "ritz1"

# Body-only edits to `plain` (non-generic) and to `Pair.sum` (method of a
# plain impl). Each makes the stripped body reach something an unstripped
# importer would pick up: a generic instantiation (monomorph walks every
# body) or an Option$ type (the emitter's tagged-enum scan walks every body).
BODY_EDITS = {
    "generic_call": ("    y * 2\n",
                     "    let q: i32 = ident<i32>(3)\n    y * 2 + q as i64\n"),
    "method_generic_call": ("        self.a + self.b\n",
                            "        let w: Wrap<i32> = Wrap<i32> { v: 1 }\n"
                            "        self.a + self.b + w.get() as i64\n"),
    "line_shift": ("    y * 2\n", "    let z: i64 = y\n\n\n\n    z * 2\n"),
}


def _ritz1(main: Path, out: Path) -> None:
    env = dict(os.environ, RITZ_PATH=str(RITZ_DIR))
    r = subprocess.run([str(RITZ1_BIN), str(main), "-o", str(out)],
                       capture_output=True, text=True, cwd=str(main.parent),
                       env=env, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.integration
@pytest.mark.usefixtures("ritz1_bin")  # conftest session build (#1804); fails, never skips
class TestRitz1Compiler:
    @pytest.mark.parametrize("edit", sorted(BODY_EDITS))
    def test_importer_ir_ignores_import_bodies(self, proj, store, tmp_path, edit):
        old, new = BODY_EDITS[edit]
        main = proj / "main.ritz"
        _ritz1(main, tmp_path / "before.ll")
        lib = proj / "lib.ritz"
        assert old in LIB
        lib.write_text(LIB.replace(old, new))
        _ritz1(main, tmp_path / "after.ll")
        assert (tmp_path / "after.ll").read_text() == (tmp_path / "before.ll").read_text()

    def test_import_still_compiles_its_own_bodies(self, proj, store, tmp_path):
        """Stripping applies to imports only: lib's own .ll defines them."""
        lib = proj / "lib.ritz"
        lib.write_text(LIB.replace(*BODY_EDITS["generic_call"]))
        _ritz1(lib, tmp_path / "lib.ll")
        ir = (tmp_path / "lib.ll").read_text()
        assert re.search(r"^define .*@plain\(", ir, re.M)
        assert re.search(r"^define .*@Pair_sum\(", ir, re.M)
        assert re.search(r"^define .*@ident\$i32\(", ir, re.M)

    def test_import_struct_field_types_declared(self, store, tmp_path):
        """An imported struct's generic field types come from the interface.

        Every importer emits `%Holder = type {%Vec$Item, %Option$i64}`; both
        field types were only reached through bodies that use Holder, which
        are stripped (ritzlib.argspec's ParsedArgs / Vec$ArgSlot in the gate).
        """
        d = tmp_path / "fields"
        d.mkdir()
        (d / "lib.ritz").write_text(
            "import ritzlib.gvec\nimport ritzlib.option\n\n"
            "pub struct Item\n    v: i64\n\n"
            "pub struct Holder\n    items: Vec<Item>\n    maybe: Option<i64>\n\n"
            "pub fn make() -> i64\n    var h: Holder\n"
            "    h.items = vec_new<Item>()\n"
            "    vec_push<Item>(@h.items, Item { v: 4 })\n"
            "    vec_len<Item>(@h.items)\n")
        (d / "main.ritz").write_text(
            "import lib\n\nfn main() -> i32\n    (make() - 1) as i32\n")
        ll = tmp_path / "main.ll"
        _ritz1(d / "main.ritz", ll)
        cc = subprocess.run(["clang", "-c", "-x", "ir", str(ll), "-o",
                             str(tmp_path / "main.o")], capture_output=True, text=True)
        assert cc.returncode == 0, cc.stderr

    @pytest.mark.parametrize("sym", ["ident$i64", "Wrap$i64_get"])
    def test_generic_import_body_still_instantiated(self, proj, store, tmp_path, sym):
        """Kept bodies: generic fns and methods of generic impls."""
        _ritz1(proj / "main.ritz", tmp_path / "main.ll")
        ir = (tmp_path / "main.ll").read_text()
        m = re.search(r"^define linkonce_odr i64 @%s\(.*?^}" % re.escape(sym),
                      ir, re.M | re.S)
        assert m, sym
        # The real body: returns a loaded value, not a placeholder.
        assert re.search(r"ret i64 %\.\d+", m.group(0)), m.group(0)
        assert not re.search(r"^define .*@(plain|Pair_sum)\(", ir, re.M)


# ---------------------------------------------------------------------------
# Import discovery (list_deps, build cache graph) reads interfaces too
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDiscovery:
    def _both(self, monkeypatch, fn):
        monkeypatch.setenv(mi.DISABLE_ENV, "1")
        full = fn()
        monkeypatch.delenv(mi.DISABLE_ENV)
        return full, fn()

    def test_collect_all_source_files_parity(self, proj, store, monkeypatch):
        from import_resolver import collect_all_source_files
        full, iface = self._both(
            monkeypatch, lambda: collect_all_source_files(str(proj / "main.ritz")))
        assert full == iface == [str(proj / "lib.ritz"), str(proj / "main.ritz")]

    def test_direct_imports_parity_and_warm(self, proj, store, monkeypatch):
        from import_resolver import ImportResolver
        run = lambda: ImportResolver(use_cache=False).direct_imports(  # noqa: E731
            str(proj / "main.ritz"))
        full, iface = self._both(monkeypatch, run)
        assert full == iface == [str(proj / "lib.ritz")]
        mi.PARSED.clear()
        run()
        assert mi.PARSED == []
