"""A generic instance only a fn-pointer type names is declared (AGAST #3979).

angelo's `resolve_composite(.., lookup_outline: fn(u16) -> Option<GlyphOutline>)`
calls through the param and binds the result; nothing else in its module
names `Option<GlyphOutline>`.  ritz1 scanned a fn's own params / return and
its lets' declared types for the Option / Result instances to declare, but
never the signature a fn type carries, so `alloca %Option$O` was an unsized
type clang refused (no Ritz location).  ritz0 compiled it.

Each row is the module under test (`lib.ritz`, compiled on its own, as
build.py compiles every module) and a driver (`main.ritz`) that imports it
and defines the fns it calls through.  The driver names the instance itself,
which is why only the separate compile shows the bug.  A `lib` reaches a
driver fn by `extern fn addr(..) -> *u8` so that no imported signature names
the instance for it.  One row per slot a fn type can sit in: a param, a
typed `let`, a fn's return, a struct field, an array field's element; each
for an Option / Result (the emitter declares those) and for a user generic
enum's instance (monomorph records those).  A field was only declared when
something else in the module named the instance too.

A param of a fn type inside a generic fn's body needs no row: the
specialised clone's signature and lets are scanned as a concrete fn's.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

P = "pub struct P\n    n: i32\n"
SLOT = "pub enum Slot<T>\n    Full(T)\n    Empty\n"
EXTERN = "extern fn addr(k: i32) -> *u8\n"


def _driver(ty, full, empty):
    """main.ritz: fns `a` (`full`) and `b` (`empty`) of type `fn() -> ty`, and
    `addr(k)`, `a` for k == 0 else `b`; exits get(0) * 10 + get(1)."""
    return (f"import lib\nfn a() -> {ty}\n    {full}\nfn b() -> {ty}\n    {empty}\n"
            "pub fn addr(k: i32) -> *u8\n    if k == 0\n        return a as *u8\n"
            "    b as *u8\nfn main() -> i32\n    get(0) * 10 + get(1)\n")


OPTION = _driver("Option<P>", "Some(P { n: 4 })", "None")
RESULT = _driver("Result<P, i32>", "Ok(P { n: 5 })", "Err(3)")
SLOT_P = _driver("Slot<P>", "Full(P { n: 4 })", "Empty")
# get(k)'s tail: `r` matched, 9 for the empty variant.
MATCH_OPTION = "    match r\n        Some(p) => p.n\n        None => 9\n"
MATCH_SLOT = "    match r\n        Full(p) => p.n\n        Empty => 9\n"


def _let(ty, tail):
    return (EXTERN + f"pub fn get(k: i32) -> i32\n    let f: fn() -> {ty} = addr(k)\n"
            "    let r = f()\n" + tail)


def _returned(ty, tail):
    return (EXTERN + f"fn pick(k: i32) -> fn() -> {ty}\n    addr(k)\n"
            "pub fn get(k: i32) -> i32\n    let r = pick(k)()\n" + tail)


def _field(ty, tail):
    return (EXTERN + f"pub struct H\n    f: fn() -> {ty}\n"
            "pub fn get(k: i32) -> i32\n    let h = H { f: addr(k) }\n    let r = h.f()\n" + tail)


# `[2]fn() -> ty` field: the element's signature is the field's elem_fn_sig.
def _elem(ty, tail):
    return (EXTERN + f"pub struct H\n    fs: [2]fn() -> {ty}\n"
            "pub fn get(k: i32) -> i32\n    var h: H\n    h.fs[0] = addr(k)\n"
            "    let r = (h.fs[0])()\n" + tail)


# name -> (lib.ritz, main.ritz, exit code)
ROWS = {
    # The ticket's repro, verbatim but for `pub`.
    "param": (
        ("pub struct O\n    n: i32\n"
         "pub fn resolve(ids: i32, look: fn(u16) -> Option<O>) -> i32\n"
         "    let r = look(ids as u16)\n    let o = match r\n        Some(o) => o\n"
         "        None => return 0\n    o.n\n"),
        ("import lib\nfn mk(x: u16) -> Option<O>\n    if x == 0\n        return None\n"
         "    Some(O { n: x as i32 + 1 })\n"
         "fn main() -> i32\n    resolve(6, mk) * 10 + resolve(0, mk)\n"),
        70),
    "let": (P + _let("Result<P, i32>", "    match r\n        Ok(p) => p.n\n        Err(e) => e\n"),
            RESULT, 53),
    "returned": (P + _returned("Option<P>", MATCH_OPTION), OPTION, 49),
    "field": (P + _field("Option<P>", MATCH_OPTION), OPTION, 49),
    "elem": (P + _elem("Option<P>", MATCH_OPTION), OPTION, 49),
    "user_generic_param": (
        P + SLOT + "pub fn get(k: i32, look: fn(i32) -> Slot<P>) -> i32\n    let r = look(k)\n"
        + MATCH_SLOT,
        ("import lib\nfn look(k: i32) -> Slot<P>\n    if k == 0\n"
         "        return Full(P { n: 4 })\n    Empty\n"
         "fn main() -> i32\n    get(0, look) * 10 + get(1, look)\n"),
        49),
    "user_generic_let": (P + SLOT + _let("Slot<P>", MATCH_SLOT), SLOT_P, 49),
    "user_generic_returned": (P + SLOT + _returned("Slot<P>", MATCH_SLOT), SLOT_P, 49),
    "user_generic_field": (P + SLOT + _field("Slot<P>", MATCH_SLOT), SLOT_P, 49),
    "user_generic_elem": (P + SLOT + _elem("Slot<P>", MATCH_SLOT), SLOT_P, 49),
}


def _compile(request, compiler, src, work):
    ll = work / f"{src.stem}.ll"
    env = dict(os.environ, RITZ_PATH=f"{work}:{RITZ_ROOT}", RITZ_CACHE_DIR=str(work / "cas"))
    if compiler == "ritz0":
        proc = run_ritz0(["--no-runtime", str(src), "-o", str(ll)], cwd=work, env=env,
                         timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=work, env=env,
                              capture_output=True, text=True, timeout=300, check=False)
    assert proc.returncode == 0, f"{compiler} refused {src.name}:\n{(proc.stdout + proc.stderr)[-2000:]}"
    return ll


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ROWS))
def test_a_fn_types_instance_is_declared(request, tmp_path, compiler, name):
    lib, main, code = ROWS[name]
    (tmp_path / "lib.ritz").write_text(lib)
    (tmp_path / "main.ritz").write_text(main)
    lls = [_compile(request, compiler, tmp_path / f"{m}.ritz", tmp_path) for m in ("lib", "main")]
    exe = tmp_path / "prog"
    link = fast_link.clang(["clang", "-w", *map(str, lls), str(RITZ_START), "-o", str(exe),
                            "-nostdlib"], cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}, {name}: would not link:\n{link.stderr[-2000:]}"
    assert subprocess.run([str(exe)], check=False, timeout=60).returncode == code, f"{compiler}, {name}"
