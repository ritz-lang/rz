"""AGAST #3326: ritz0 knows the built-in StrView struct with no import.

THE BUG

Every "..." literal is a StrView, import or not, but ritz0 only registered
StrView's struct when ``ritzlib.strview`` was imported or a type it lowered
named StrView.  In a file that imported nothing:

    let v: StrView = "abc"
    let n: i64 = v.len          # ValueError: Cannot determine struct type
    StrView { ptr: p, len: n }  # ValueError: Unknown struct: StrView

ritz1 compiled both.

THE FIX

A ``StrView { .. }`` literal registers the built-in ``{ *u8, i64 }`` struct
(``_ensure_strview_type``), and a field read on a bare ``{ i8*, i64 }``
value whose Ritz type is StrView names its struct from that type.  A
declared or imported ``struct StrView`` (``ritzlib.strview``) stays the only
definition.  Registering StrView up front instead would retype every literal
in the module and so refuse ``let s: Span<u8> = "hello"``, which ritz0 only
accepts without the import (test_sstring, test_cs_mixed).

ORACLE

The field reads run under all three compilers in the matrix file
``ritz0/test/test_strview_builtin_no_import.ritz``.  Here: the struct literal
on its own, printed with no field read, so it fails for the literal and not
for ``.len``; and the import case, pinned to one StrView type in the IR.
"""

import re

import pytest

from test_eprint_interpolation import _compile, _run

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("ritz1_bin")]

LITERAL = """\
pub fn main() -> i32
    let w: StrView = StrView { ptr: c"wxyz" + 1, len: 2 }
    print("{w}|")
    0
"""

IMPORTED = """\
import ritzlib.strview

pub fn main() -> i32
    let v: StrView = "abc"
    let w: StrView = StrView { ptr: v.ptr, len: v.len - 1 }
    print("{w}|{v}|")
    0
"""


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_struct_literal_without_import(tmp_path, compiler):
    out, _ = _run(compiler, tmp_path, "literal", LITERAL)
    assert out == b"xy|"


def test_import_keeps_one_strview_type(tmp_path):
    out, _ = _run("ritz0", tmp_path, "imported", IMPORTED)
    assert out == b"ab|abc|"
    _, ll = _compile("ritz0", tmp_path, "imported_ir", IMPORTED)
    defs = re.findall(r'^%"?[\w.]*StrView"? = type', ll.read_text(), re.M)
    assert len(defs) == 1, defs
