"""AGAST #3466 (LARB R54): each name in `import m { … }` must be declared at
the top level of `m`, or re-exported by `m`'s `pub import`. Otherwise:

    main.ritz:1:17: `nope` is not defined in a

located at the name. Names `m` reaches only through its own plain `import`
don't count. Private types and consts count (type privacy isn't enforced);
a private fn in the list gets §15.2's error at the import. The list is
checked but still doesn't filter.
"""

import os
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent

B = """\
pub fn two() -> i32
    2
"""


def _run(tmp_path, a_src, main_src):
    (tmp_path / "a.ritz").write_text(a_src)
    (tmp_path / "b.ritz").write_text(B)
    (tmp_path / "main.ritz").write_text(main_src)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    return run_ritz0(["main.ritz", "-o", str(tmp_path / "main.ll")],
                     cwd=tmp_path, env=env, timeout=300)


def _errors(tmp_path, a_src, main_src):
    """The compile fails with no .ll; its stderr's diagnostic lines."""
    comp = _run(tmp_path, a_src, main_src)
    assert comp.returncode != 0, comp.stderr
    assert not (tmp_path / "main.ll").exists()
    return [line for line in comp.stderr.splitlines()
            if "main.ritz:" in line or ": note: " in line]


def _compiles(tmp_path, a_src, main_src):
    comp = _run(tmp_path, a_src, main_src)
    assert comp.returncode == 0, comp.stderr


def test_undefined_name_is_an_error_at_the_name(tmp_path):
    a = "pub fn one() -> i32\n    1\n"
    main = """\
import a { one, nope }

pub fn main() -> i32
    one()
"""
    assert _errors(tmp_path, a, main) == [
        "Error: main.ritz:1:17: `nope` is not defined in a"]


def test_name_reached_only_through_a_plain_import_is_an_error(tmp_path):
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
    assert _errors(tmp_path, a, main) == [
        "Error: main.ritz:3:5: `two` is not defined in a"]


@pytest.mark.parametrize("reexport", ["pub import b", "pub import b { two }"])
def test_pub_import_reexport_is_defined(tmp_path, reexport):
    a = f"{reexport}\n\npub fn one() -> i32\n    1\n"
    main = """\
import a { one, two }

pub fn main() -> i32
    one() + two()
"""
    _compiles(tmp_path, a, main)


def test_private_type_and_const_are_accepted(tmp_path):
    a = "struct P\n    v: i32\n\nconst K: i32 = 3\n"
    main = """\
import a { P, K }

pub fn main() -> i32
    let p = P { v: K }
    p.v
"""
    _compiles(tmp_path, a, main)


def test_private_fn_is_section_15_2_error_at_the_import(tmp_path):
    """Refused even though main never calls it: the list names it."""
    a = "fn helper() -> i32\n    7\n\npub fn one() -> i32\n    1\n"
    main = """\
import a { one, helper }

pub fn main() -> i32
    one()
"""
    assert _errors(tmp_path, a, main) == [
        ("Error: main.ritz:1:17: `helper` is private to a.ritz; "
         "mark it `pub` (#3413)"),
        f"{tmp_path / 'a.ritz'}:1:1: note: `helper` is declared here",
    ]
