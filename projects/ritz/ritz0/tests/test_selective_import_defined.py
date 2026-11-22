"""LARB R54 (LANGUAGE_SPEC §15.1): each name in `import m { … }` must be
declared at the top level of `m`, or re-exported by `m`'s `pub import`.
Otherwise it is an error at the name:

    main.ritz:1:17: `nope` is not defined in a

Names `m` reaches only through its own plain `import` don't count. Private
types and consts count (type privacy isn't enforced); a private fn in the
list gets §15.2's error at the import, with a note at its declaration. The
list is checked but still doesn't filter.

ritz0: AGAST #3466. ritz1 and ritz1_selfhosted: #3467, checked after import
resolution and before emission. Every row runs on all three compilers.
The tempest row is #4307: the `ritzlib.hashmap` list network.ritz used to
write, which built only because no compiler checked the list.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

B = """\
pub fn two() -> i32
    2

pub fn three() -> i32
    3
"""


def _run(compiler, tmp_path, a_src, main_src):
    (tmp_path / "a.ritz").write_text(a_src)
    (tmp_path / "b.ritz").write_text(B)
    (tmp_path / "main.ritz").write_text(main_src)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}",
               RITZ_CACHE_DIR=str(tmp_path / "cas"))
    if compiler == "ritz0":
        return run_ritz0(["main.ritz", "-o", str(ll)], cwd=tmp_path, env=env,
                         timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries first.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), "main.ritz", "-o", str(ll)],
                          cwd=tmp_path, env=env, capture_output=True,
                          text=True, timeout=120, check=False)


def _errors(compiler, tmp_path, a_src, main_src):
    """The compile fails with no .ll; its diagnostics as `main.ritz:L:C:
    message` and `<file>:L:C: note: …`, whichever compiler's prefix."""
    comp = _run(compiler, tmp_path, a_src, main_src)
    assert comp.returncode != 0, comp.stderr
    assert not (tmp_path / "main.ll").exists()
    lines = []
    for line in comp.stderr.splitlines():
        for prefix in ("Error: ", "Compiler error: ", "error: "):
            line = line.removeprefix(prefix)
        if line.startswith("main.ritz:"):
            lines.append(line.replace(": error: ", ": ", 1))
        elif ": note: " in line:
            # The note's file is absolute on ritz0; compare its basename.
            lines.append(os.path.basename(line.split(":", 1)[0]) + ":"
                         + line.split(":", 1)[1])
    return lines


def _compiles(compiler, tmp_path, a_src, main_src):
    comp = _run(compiler, tmp_path, a_src, main_src)
    assert comp.returncode == 0, comp.stderr
    assert (tmp_path / "main.ll").exists()


@pytest.mark.parametrize("compiler", COMPILERS)
def test_undefined_name_is_an_error_at_the_name(tmp_path, compiler):
    a = "pub fn one() -> i32\n    1\n"
    main = """\
import a { one, nope }

pub fn main() -> i32
    one()
"""
    assert _errors(compiler, tmp_path, a, main) == [
        "main.ritz:1:17: `nope` is not defined in a"]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_reported_once_when_aliases_parse_twice(tmp_path, compiler):
    """A type alias makes ritz1 parse everything a second time (#1475);
    the error is reported once, from the first pass."""
    a = "pub fn one() -> i32\n    1\n"
    main = """\
import a { one, nope }

type N = i32

pub fn main() -> i32
    let n: N = one()
    n
"""
    assert _errors(compiler, tmp_path, a, main) == [
        "main.ritz:1:17: `nope` is not defined in a"]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_each_undefined_name_is_reported(tmp_path, compiler):
    """One error per name, in source order, in a dotted module path."""
    a = "pub fn one() -> i32\n    1\n"
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.ritz").write_text(a)
    main = """\
import pkg.m { nope, one, gone }

pub fn main() -> i32
    one()
"""
    assert _errors(compiler, tmp_path, a, main) == [
        "main.ritz:1:16: `nope` is not defined in pkg.m",
        "main.ritz:1:27: `gone` is not defined in pkg.m"]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_name_reached_only_through_a_plain_import_is_an_error(tmp_path,
                                                             compiler):
    """`a` imports `b`; that doesn't make `two` a name `a` defines."""
    a = "import b\n\npub fn one() -> i32\n    two() - 1\n"
    main = """\
import a {
    one,
    two,
}

pub fn main() -> i32
    one()
"""
    assert _errors(compiler, tmp_path, a, main) == [
        "main.ritz:3:5: `two` is not defined in a"]


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("reexport", ["pub import b", "pub import b { two }"])
def test_pub_import_reexport_is_defined(tmp_path, compiler, reexport):
    a = f"{reexport}\n\npub fn one() -> i32\n    1\n"
    main = """\
import a { one, two }

pub fn main() -> i32
    one() + two()
"""
    _compiles(compiler, tmp_path, a, main)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_pub_import_list_reexports_only_its_names(tmp_path, compiler):
    """`pub import b { two }` re-exports `two`, not the rest of b."""
    a = "pub import b { two }\n\npub fn one() -> i32\n    1\n"
    main = """\
import a { one, three }

pub fn main() -> i32
    one()
"""
    assert _errors(compiler, tmp_path, a, main) == [
        "main.ritz:1:17: `three` is not defined in a"]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_kind_of_declaration_is_defined(tmp_path, compiler):
    """Private types and consts count; so do an enum, a type alias, a
    trait, a global and an `extern fn`."""
    a = """\
struct P
    v: i32

const K: i32 = 3

pub enum E
    X
    Y

pub type Alias = i32

pub trait Tr
    fn t(self: @Self) -> i32

var G: i32 = 0

extern fn ext_sym() -> i32
"""
    main = """\
import a { P, K, E, Alias, Tr, G, ext_sym }

pub fn main() -> i32
    let p = P { v: K }
    p.v
"""
    _compiles(compiler, tmp_path, a, main)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_declaration_gated_for_another_target_is_defined(tmp_path,
                                                         compiler):
    """`[[target_os]]` gates what is compiled, not what a module defines:
    ritzlib.sys's harland-only names are listed by code built for linux
    too (prism, rzsh, indium)."""
    a = """\
[[target_os = "harland"]]
pub fn h_only() -> i32
    1

[[target_os = "harland"]]
const H_K: i64 = 210

[[target_os = "harland"]]
pub struct HS
    v: i32

pub fn one() -> i32
    1
"""
    main = """\
import a { one, h_only, H_K, HS }

pub fn main() -> i32
    one()
"""
    _compiles(compiler, tmp_path, a, main)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_private_fn_is_section_15_2_error_at_the_import(tmp_path, compiler):
    """Refused even though main never calls it: the list names it."""
    a = "fn helper() -> i32\n    7\n\npub fn one() -> i32\n    1\n"
    main = """\
import a { one, helper }

pub fn main() -> i32
    one()
"""
    assert _errors(compiler, tmp_path, a, main) == [
        ("main.ritz:1:17: `helper` is private to a.ritz; "
         "mark it `pub` (#3413)"),
        "a.ritz:1:1: note: `helper` is declared here",
    ]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_tempest_network_hashmap_list_is_refused(tmp_path, compiler):
    """AGAST #4307: tempest/lib/network.ritz's old list. `HashMap` and
    `hashmap_new` exist since #4306; `hashmap_set` never did (it is
    `hashmap_insert`, now `HashMap.insert`).  #4445 moved `hashmap_get`
    to `HashMap.get` too, so it no longer names a hashmap item."""
    main = """\
import ritzlib.hashmap { HashMap, hashmap_new, hashmap_set }

pub fn main() -> i32
    0
"""
    assert _errors(compiler, tmp_path, "", main) == [
        "main.ritz:1:48: `hashmap_set` is not defined in ritzlib.hashmap"]
