"""AGAST #3493 (LARB R65, LANGUAGE_SPEC §12.2): where an `impl` may live.

An inherent `impl T` is in the file that declares `T`. A trait impl is in the
type's file or the trait's file; a trait the compiler knows (Drop, Index…)
counts as the type's file. Otherwise, at the impl's type name:

    main.ritz:4:6: `Foo` is declared in a.ritz: its `impl` must be there (§12.2)

Before: two files adding `Foo.tag` failed at link with no location, and a
method added in one file leaked to every file that imported it.

An impl covers every instantiation: `impl<T> G<T>`, never `impl G<u8>`:

    main.ritz:4:6: an impl covers every instantiation of `G`: write `impl<T> G<T>`

Before: `impl G<u8>` alone was an unlocated ValueError, and next to
`impl<T> G<T>` ritz0 silently ran the generic body. ritz1's half is #3494.
"""

import os
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from test_ref_into_value import _link

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent

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


def _compile(tmp_path, main_src):
    (tmp_path / "a.ritz").write_text(A)
    (tmp_path / "b.ritz").write_text(B)
    (tmp_path / "main.ritz").write_text(main_src)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    return run_ritz0(["main.ritz", "-o", str(tmp_path / "main.ll")],
                     cwd=tmp_path, env=env, timeout=300)


def _located(marked):
    """`marked` without its `^`, and where the `^` was as `line:col`."""
    before = marked[:marked.index("^")]
    return (marked.replace("^", "", 1),
            f"{before.count(chr(10)) + 1}:{len(before) - before.rfind(chr(10))}")


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
    # One instantiation alone (was an unlocated ValueError).
    "one_instantiation": ("""\
struct G<T>
    v: T

impl ^G<u8>
    fn get(self: @G<u8>) -> u8
        self.v

pub fn main() -> i32
    0
""", every("G", "impl<T> G<T>")),
    # Next to the generic impl (ritz0 silently ran the generic body).
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


@pytest.mark.parametrize("row", sorted(REFUSED))
def test_misplaced_or_partial_impl_refused(tmp_path, row):
    marked, message = REFUSED[row]
    src, where = _located(marked)
    comp = _compile(tmp_path, src)
    assert comp.returncode != 0, f"accepted {row}:\n{src}"
    assert not (tmp_path / "main.ll").exists()
    assert f"main.ritz:{where}: {message}" in comp.stderr, comp.stderr[-2000:]


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


def test_trait_impl_in_the_traits_file_compiles_and_runs(tmp_path):
    comp = _compile(tmp_path, TRAITS_FILE)
    assert comp.returncode == 0, comp.stderr[-2000:]
    link, exe = _link("ritz0", tmp_path / "main.ll", tmp_path)
    assert link.returncode == 0, link.stderr[-2000:]
    import subprocess
    assert subprocess.run([str(exe)], timeout=60).returncode == 42
