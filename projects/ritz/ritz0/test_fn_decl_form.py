"""AGAST #1900: the declaration-only fn form, `fn ... = extern`.

A fn or method whose header ends in `= extern` instead of a body declares
"this signature; the body lives in another object, under the same symbol and
ABI as the defining module". It exists for Ritz-source module interfaces
(#1901): the stripped text of a module must be able to say that, at top
level and inside a plain `impl`. `extern fn` can't (C-style, top level only,
no pub/attributes) and a `pass` body is ill-typed and looks like a real body.

THE CONTRACT (LANGUAGE_SPEC §5.3)

* Calling a declared fn/method emits exactly the `declare` that importing the
  defining module emits (test_declare_matches_import).
* Linking the declaring object with the defining one runs
  (test_links_against_definition).
* Bodies an importer instantiates can't be declaration-only: generic fns,
  methods of generic impls, async fns (ritz0; ritz1 has no async). Trait
  methods are already signatures, and a `[[test]]` needs its body. Each is a
  located parse-time error naming the item, in every compiler.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
NEEDLE = "cannot be declaration-only"

pytestmark = pytest.mark.integration


def _compile(compiler, tmp_path, files, main, extra=()):
    for name, src in files.items():
        (tmp_path / f"{name}.ritz").write_text(src)
    path = tmp_path / f"{main}.ritz"
    ll = tmp_path / f"{main}_{compiler}.ll"
    if ll.exists():
        ll.unlink()
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env,
                         timeout=300), ll
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


def _compile_ok(compiler, tmp_path, files, main, extra=()):
    proc, ll = _compile(compiler, tmp_path, files, main, extra)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected {main}:\n{out}"
    return ll


# The defining module: a free fn, and a plain impl whose methods cover a
# scalar return, a struct returned by value, and a void mutating receiver.
LIB = """\
pub struct Pt
    x: i64
    y: i64

pub fn add(a: i64, b: i32) -> i64
    a + b as i64

impl Pt
    fn sum(self: *Pt) -> i64
        self.x + self.y

    fn swapped(self: *Pt) -> Pt
        Pt { x: self.y, y: self.x }

    pub fn bump(self: *Pt, by: i64)
        self.x = self.x + by
"""

MAIN_BODY = """
fn main() -> i32
    var p: Pt = Pt { x: 2, y: 5 }
    p.bump(1)
    let q: Pt = p.swapped()
    (add(p.sum(), 3) + q.x * 10) as i32
"""
EXPECTED_EXIT = 61  # p = (3, 5): add(8, 3) + 5 * 10

# The same interface, written with the declaration form instead of imported.
DECLS = """\
pub struct Pt
    x: i64
    y: i64

pub fn add(a: i64, b: i32) -> i64 = extern

impl Pt
    fn sum(self: *Pt) -> i64 = extern

    fn swapped(self: *Pt) -> Pt = extern

    pub fn bump(self: *Pt, by: i64) = extern
"""

MAIN_DECL = DECLS + MAIN_BODY
MAIN_IMPORT = "import lib\n" + MAIN_BODY

SYMBOLS = ("add", "Pt_sum", "Pt_swapped", "Pt_bump")


def _declares(ll: Path) -> dict:
    """symbol -> its `declare` line, for SYMBOLS."""
    found = {}
    for line in ll.read_text().splitlines():
        if not line.startswith("declare"):
            continue
        for sym in SYMBOLS:
            if re.search(rf"@\"?{sym}\"?\(", line):
                assert sym not in found, f"{sym} declared twice in {ll.name}"
                found[sym] = line
    return found


@pytest.mark.parametrize("compiler", COMPILERS)
def test_declare_matches_import(compiler, tmp_path):
    """The declaration form produces the same `declare` as an import does."""
    files = {"lib": LIB, "main_decl": MAIN_DECL, "main_import": MAIN_IMPORT}
    decl = _declares(_compile_ok(compiler, tmp_path, files, "main_decl"))
    imp = _declares(_compile_ok(compiler, tmp_path, files, "main_import"))
    assert set(imp) == set(SYMBOLS), f"{compiler}: import oracle declares {sorted(imp)}"
    assert decl == imp


@pytest.mark.parametrize("compiler", COMPILERS)
def test_decl_defines_nothing(compiler, tmp_path):
    """A declared fn is never `define`d by the declaring module."""
    ll = _compile_ok(compiler, tmp_path, {"main_decl": MAIN_DECL}, "main_decl")
    ir = ll.read_text()
    for sym in SYMBOLS:
        assert not re.search(rf"^define .*@\"?{sym}\"?\(", ir, re.M), \
            f"{compiler} defined {sym}:\n{ir}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_links_against_definition(compiler, tmp_path):
    files = {"lib": LIB, "main_decl": MAIN_DECL}
    # A library module, as build.py compiles one: ritz0 gives its non-pub
    # fns external linkage only under --no-runtime (ritz1 always does).
    extra = ("--no-runtime",) if compiler == "ritz0" else ()
    lib_ll = _compile_ok(compiler, tmp_path, files, "lib", extra)
    main_ll = _compile_ok(compiler, tmp_path, files, "main_decl")
    exe = tmp_path / f"prog_{compiler}"
    cmd = ["clang", "-Wno-override-module", str(main_ll), str(lib_ll),
           "-o", str(exe), "-nostdlib", "-no-pie"]
    if compiler != "ritz0":
        cmd.insert(1, str(RITZ_START))
    link = fast_link.clang(cmd, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} did not link:\n{link.stderr[-2000:]}"
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == EXPECTED_EXIT


@pytest.mark.parametrize("compiler", COMPILERS)
def test_unused_decl_compiles(compiler, tmp_path):
    src = DECLS + "\nfn main() -> i32\n    0\n"
    _compile_ok(compiler, tmp_path, {"t": src}, "t")


# --- rejections ------------------------------------------------------------

REJECTS = {
    "generic_fn": ("""\
fn ident<T>(x: T) -> T = extern

fn main() -> i32
    0
""", "t.ritz:1", "ident"),
    "pub_generic_fn": ("""\
pub fn ident<T>(x: T) -> T = extern

fn main() -> i32
    0
""", "t.ritz:1", "ident"),
    "generic_impl_method": ("""\
struct W<T>
    v: T

impl<T> W<T>
    fn get(self: *W<T>) -> T = extern

fn main() -> i32
    0
""", "t.ritz:5", "get"),
    "trait_method": ("""\
trait Shape
    fn area(self) -> i64 = extern

fn main() -> i32
    0
""", "t.ritz:2", "area"),
    "test_fn": ("""\
[[test]]
fn test_it() -> i32 = extern

fn main() -> i32
    0
""", "t.ritz:2", "test_it"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(REJECTS))
def test_rejected(compiler, case, tmp_path):
    src, where, name = REJECTS[case]
    proc, _ = _compile(compiler, tmp_path, {"t": src}, "t")
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {case}:\n{out}"
    assert NEEDLE in out, f"{compiler}: rejected {case}, but not as a declaration:\n{out}"
    assert re.search(rf"{re.escape(where)}\b", out), (
        f"{compiler}: error not located at {where}:\n{out}")
    assert f"'{name}'" in out, f"{compiler}: error does not name '{name}':\n{out}"


def test_async_rejected_ritz0(tmp_path):
    src = "async fn later() -> i64 = extern\n\nfn main() -> i32\n    0\n"
    proc, _ = _compile("ritz0", tmp_path, {"t": src}, "t")
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and NEEDLE in out and "'later'" in out, out


@pytest.mark.unit
def test_ritz0_ast():
    from parser import parse
    m = parse("fn f(a: i32) -> i32 = extern\n\nfn g() -> i32\n    0\n")
    f, g = m.items
    assert f.is_decl and f.body.stmts == [] and f.body.expr is None
    assert not g.is_decl
