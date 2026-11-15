#!/usr/bin/env python3
"""sizeof of a struct whose field is spelled through a type alias (AGAST #2151).

`_ritz_type_size_and_align` never resolved aliases, so a field `g: Grid`
(`type Grid = [4][4]u8`) hit the unknown-type fallback of (8, 8): `sizeof(B)`
was 24 while the `{i8, [4 x [4 x i8]], i8}` ritz0 emits for B is 18 bytes.
The LLVM layout already resolved the alias, so sizeof and the layout ritz0
itself emits disagreed.

Each probe is checked against LLVM's own layout of the emitted IR, reusing
the oracle from test_sizeof_enum_field.py. One probe per alias shape: N-D
array, 1-D array, struct, alias of an alias, and an array of an alias.
"""

import os
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from test_sizeof_enum_field import _llvm_abi_sizes, _sizeof_constants

RITZ_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.integration

SOURCE = """\
type Grid = [4][4]u8
type Row = [4]u8
type PA = P
type G2 = Grid
type Rows = [3]Row

struct P
    a: u8
    b: u32

struct NdAlias
    pre: u8
    g: Grid
    post: u8

struct RowAlias
    pre: u8
    r: Row
    post: u8

struct StructAlias
    pre: u8
    p: PA
    post: u8

struct ChainAlias
    pre: u8
    g: G2
    post: u8

struct ArrayOfAlias
    pre: u8
    rs: Rows
    post: u8

fn sz_NdAlias() -> i64
    return sizeof(NdAlias)
fn sz_RowAlias() -> i64
    return sizeof(RowAlias)
fn sz_StructAlias() -> i64
    return sizeof(StructAlias)
fn sz_ChainAlias() -> i64
    return sizeof(ChainAlias)
fn sz_ArrayOfAlias() -> i64
    return sizeof(ArrayOfAlias)

fn main() -> i32
    0
"""

# Readable cross-check of the LLVM oracle.
EXPECTED = {
    "NdAlias": 18,  # i8 + [4 x [4 x i8]] + i8, all 1-aligned
    "RowAlias": 6,  # i8 + [4 x i8] + i8
    "StructAlias": 16,  # i8, pad 3, %P (8, 4-aligned), i8, pad 3
    "ChainAlias": 18,  # G2 -> Grid -> [4][4]u8
    "ArrayOfAlias": 14,  # i8 + [3 x [4 x i8]] + i8
}


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sizeof_alias_field")
    src = tmp / "unit.ritz"
    src.write_text(SOURCE)
    out = tmp / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    res = run_ritz0([str(src), "-o", str(out)], env=env)
    assert res.returncode == 0, res.stderr
    return out.read_text()


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_sizeof_matches_emitted_llvm_layout(compiled, name):
    consts = _sizeof_constants(compiled)
    abi = _llvm_abi_sizes(compiled)
    assert name in abi, f"no emitted type for {name}: {sorted(abi)}"
    assert consts[name] == abi[name], (
        f"sizeof({name}) = {consts[name]} but LLVM lays the emitted type out "
        f"in {abi[name]} bytes"
    )
    assert consts[name] == EXPECTED[name]
