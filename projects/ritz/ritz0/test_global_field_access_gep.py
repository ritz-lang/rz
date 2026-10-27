#!/usr/bin/env python3
"""A field read on a struct place GEPs to the field; it never loads the struct.

AGAST #1914. `g.count` on a global `var g: Big` was emitted as::

    %v = load %Big, %Big* @g        ; the whole struct, as one SSA value
    %c = extractvalue %Big %v, 2

Locals already took the GEP path; globals, and nested chains on either
(`l.inner.x`, `g.inner.x`), did not. LLVM's -O2 folds the aggregate load away,
but at -O0 SelectionDAG expands it into one node per scalar. http's
HpackDecoder is ~74 KB (an [8192 x i8] plus two 64-entry arrays) and its test
file reads `g_decoder.<field>` 20 times: the -O0 lowering of that one test
binary took 29-56 s and was the critical path of `rz test --all`.

These tests pin the IR shape (no first-class load of a struct-typed place for
a field read) and that the values read are still right.
"""

import re
import sys
import textwrap
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).parent.resolve()
RITZ_DIR = RITZ0_DIR.parent
sys.path.insert(0, str(RITZ0_DIR))

import test_runner  # noqa: E402

pytestmark = pytest.mark.integration

SOURCE = textwrap.dedent(
    """\
    struct Inner
        pad: [4096]u8
        x: i64

    struct Big
        inner: Inner
        bytes: [8192]u8
        count: i32

    var g: Big

    fn global_count() -> i32
        g.count

    fn global_nested() -> i64
        g.inner.x

    fn local_nested() -> i64
        var l: Big
        let p: *Inner = @l.inner
        p.x = 9
        l.inner.x
    """
)


def _ir(tmp_path) -> str:
    src = tmp_path / "unit.ritz"
    src.write_text(SOURCE)
    out = tmp_path / "unit.ll"
    run_ritz0([str(src), "-o", str(out), "--no-runtime"])
    return out.read_text()


def _function(ir: str, name: str) -> str:
    match = re.search(r'define [^\n]*@"?%s"?\(.*?\n}\n' % re.escape(name), ir, re.S)
    assert match, f"{name} not in IR"
    return match.group(0)


def _aggregate_loads(body: str):
    """First-class loads of a named struct value (`load %"struct...."`)."""
    return re.findall(r'= load %"?struct\.[^,]*', body)


@pytest.mark.parametrize("fn", ["global_count", "global_nested", "local_nested"])
def test_field_read_does_not_load_the_struct(tmp_path, fn):
    body = _function(_ir(tmp_path), fn)
    assert _aggregate_loads(body) == [], (
        f"{fn} loads a whole struct to read one field:\n{body}")


def test_field_reads_through_gep_read_the_right_values(tmp_path, monkeypatch):
    """The GEP path reads the same fields the aggregate path did."""
    monkeypatch.setenv("RITZ_PATH", str(RITZ_DIR))
    (tmp_path / "ritz.toml").write_text(textwrap.dedent(f"""\
        [package]
        name = "global_field_gep"
        version = "0.1.0"
        sources = ["test"]

        [dependencies]
        ritzlib = {{ path = "{RITZ_DIR / 'ritzlib'}", sources = ["."] }}
        """))
    (tmp_path / "test").mkdir()
    test_file = tmp_path / "test" / "test_global_field_gep.ritz"
    test_file.write_text(SOURCE + textwrap.dedent("""\

        [[test]]
        fn test_global_fields() -> i32
            g.count = 7
            g.inner.x = 11
            g.bytes[8191] = 3
            assert global_count() == 7
            assert global_nested() == 11
            assert g.bytes[8191] == 3
            assert g.inner.pad[0] == 0
            0

        [[test]]
        fn test_local_nested() -> i32
            assert local_nested() == 9
            0
        """))
    passed, failed, failures = test_runner.run_test_file(str(test_file))
    assert (passed, failed) == (2, 0), failures


ASSIGN_SOURCE = SOURCE + textwrap.dedent("""\

    fn global_assign()
        g.count = 1
        g.inner.x = 2

    fn local_assign() -> i64
        var l: Big
        l.inner.x = 3
        l.count = 4
        0
    """)


@pytest.mark.parametrize("fn", ["global_assign", "local_assign"])
def test_field_assignment_does_not_load_the_struct(tmp_path, fn):
    """`g.f = v` stores through a GEP; the struct is not loaded first."""
    src = tmp_path / "assign.ritz"
    src.write_text(ASSIGN_SOURCE)
    out = tmp_path / "assign.ll"
    run_ritz0([str(src), "-o", str(out), "--no-runtime"])
    body = _function(out.read_text(), fn)
    assert _aggregate_loads(body) == [], (
        f"{fn} loads a whole struct to assign one field:\n{body}")
