"""AGAST #3494 (LARB R65, LANGUAGE_SPEC §12.2) on ritz1 and ritz1_selfhosted.

The same rule as ritz0's test_impl_placement.py (#3493): an inherent `impl T`
is in the file that declares `T`; a trait impl is in the type's file or the
trait's file (a compiler-known trait counts as the type's); and an impl covers
every instantiation.  Here the rule runs on all three compilers.

    main.ritz:4:6: `Foo` is declared in a.ritz: its `impl` must be there (§12.2)
    main.ritz:4:6: an impl covers every instantiation of `G`: write `impl<T> G<T>`

Before: ritz1 silently kept one body per module, leaked a method through the
whole import closure, and emitted invalid IR on `impl G<u8>`.

R81's free `T` row (`impl Box<T>` without `<T>`) stays ritz0-only in
test_impl_placement.py: ritz1's half is #4002.
"""

import os
import re
import subprocess

import pytest

from ritz0_inproc import run_ritz0
from test_ref_into_value import (
    COMPILERS,
    RITZ1_BUILD,
    RITZ_ROOT,
    _link,
    _located,
)

pytestmark = pytest.mark.integration

# a.ritz declares the type; b.ritz a trait of its own.
A = """\
pub struct Foo
    x: i32

pub trait Shout
    fn shout(self: @Self) -> i32
"""

B = """\
pub trait Speak
    fn say(self: @Self) -> i32
"""


def placed(name, file):
    return f"`{name}` is declared in {file}: its `impl` must be there (§12.2)"


def every(name, write):
    return f"an impl covers every instantiation of `{name}`: write `{write}`"


def _emit(compiler, work):
    """Compile work/main.ritz (which imports work/a.ritz and b.ritz)."""
    env = dict(os.environ, RITZ_PATH=f"{work}:{RITZ_ROOT}")
    cmd = ["main.ritz", "-o", "main.ll"]
    if compiler == "ritz0":
        return run_ritz0(cmd, cwd=work, env=env, timeout=300)
    return subprocess.run([str(RITZ1_BUILD / compiler), *cmd], cwd=work,
                          env=env, capture_output=True, text=True, timeout=300)


def _workdir(tmp_path, name, compiler):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    (work / "a.ritz").write_text(A)
    (work / "b.ritz").write_text(B)
    return work


# name -> (program with `^` at the error, message)
REFUSED = {
    # An inherent impl of another file's type.
    "inherent_elsewhere": ("""\
import a { Foo }

impl ^Foo
    fn tag(self: @Foo) -> i32
        self.x

pub fn main() -> i32
    0
""", placed("Foo", "a.ritz")),
    # A trait impl in neither the type's file nor the trait's.
    "trait_in_neither": ("""\
import a { Foo }
import b { Speak }

impl Speak for ^Foo
    fn say(self: @Foo) -> i32
        self.x

pub fn main() -> i32
    0
""", placed("Foo", "a.ritz")),
    # A compiler-known trait counts as the type's file.
    "drop_elsewhere": ("""\
import a { Foo }

impl Drop for ^Foo
    fn drop(self: @&Foo)
        self.x = 0

pub fn main() -> i32
    0
""", placed("Foo", "a.ritz")),
    # One instantiation alone (ritz1 emitted invalid IR).
    "one_instantiation": ("""\
struct G<T>
    v: T

impl ^G<u8>
    fn get(self: @G<u8>) -> u8
        self.v

pub fn main() -> i32
    0
""", every("G", "impl<T> G<T>")),
    # Next to the generic impl (ritz1 silently kept one body per module).
    "beside_generic": ("""\
struct G<T>
    v: T

impl<T> G<T>
    fn get(self: @G<T>) -> i32
        1

impl ^G<u8>
    fn only(self: @G<u8>) -> i32
        2

pub fn main() -> i32
    0
""", every("G", "impl<T> G<T>")),
    # A trait impl, and a parameter fixed among several: the declared names.
    "trait_partial": ("""\
trait Speak
    fn say(self: @Self) -> i32

struct P<K, V>
    k: K
    v: V

impl<K> Speak for ^P<K, i32>
    fn say(self: @P<K, i32>) -> i32
        self.v

pub fn main() -> i32
    0
""", every("P", "impl<K, V> P<K, V>")),
    # The same parameter twice covers only P<X, X>.
    "repeated_param": ("""\
struct P<K, V>
    k: K
    v: V

impl<T> ^P<T, T>
    fn one(self: @P<T, T>) -> i32
        1

pub fn main() -> i32
    0
""", every("P", "impl<K, V> P<K, V>")),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(REFUSED))
def test_misplaced_or_partial_impl_refused(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    marked, message = REFUSED[row]
    src, where = _located(marked)
    work = _workdir(tmp_path, row, compiler)
    (work / "main.ritz").write_text(src)
    proc = _emit(compiler, work)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {row}:\n{src}"
    assert not (work / "main.ll").exists()
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    found = [(at, msg.split("; expected ")[0]) for at, msg in found]
    assert (where, message) in found, (
        f"{compiler}: {row}, wanted {where}:\n{src}\n{out[-2000:]}")


# The trait's file: legal, and the method is reached from there.
TRAITS_FILE = """\
import a { Foo }

trait Count
    fn count(self: @Self) -> i32

impl Count for Foo
    fn count(self: @Foo) -> i32
        self.x + 1

pub fn main() -> i32
    let f = Foo { x: 41 }
    f.count()
"""

# The control: an impl that declares its parameter covers every instantiation.
GENERIC_IMPL = """\
struct G<T>
    v: T

impl<T> G<T>
    fn get(self: @G<T>) -> i32
        41

pub fn main() -> i32
    let g: G<i32> = G { v: 5 }
    g.get() + 1
"""

# R36's revisit (#4294) is the one exception: a concrete instantiation of a
# built-in target in the trait's file stands (`impl Display for Span<u8>`).
SPAN_GENERIC = """\
struct Span<T>
    ptr: *T
    len: i64

trait Size
    fn size(self: @Self) -> i32

impl Size for Span<u8>
    fn size(self: @Span<u8>) -> i32
        self.len as i32

pub fn main() -> i32
    var a: [3]u8 = [1, 2, 3]
    let s: Span<u8> = Span { ptr: @a[0], len: 3 }
    s.size() * 14
"""

LEGAL = {
    "traits_file": (TRAITS_FILE, 42),
    "generic_impl": (GENERIC_IMPL, 42),
    "builtin_concrete_in_trait_file": (SPAN_GENERIC, 42),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(LEGAL))
def test_legal_impl_compiles_and_runs(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    src, code = LEGAL[row]
    work = _workdir(tmp_path, row, compiler)
    (work / "main.ritz").write_text(src)
    proc = _emit(compiler, work)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, f"{compiler} refused {row}:\n{out[-2000:]}"
    ll = work / "main.ll"
    assert ll.exists(), f"{compiler}: {row} wrote no IR"
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, f"{compiler}: {row} would not link:\n{link.stderr[-2000:]}"
    got = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert got == code, f"{compiler}: {row} returned {got}, wanted {code}"
