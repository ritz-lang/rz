#!/usr/bin/env python3
"""sizeof of a struct holding a later-declared struct by value (AGAST #1936).

`_define_struct` lays structs out in source order. When `Early` holds a
`Late` declared after it, `Late` had no layout yet, so
`_ritz_type_size_and_align` fell back to (8, 8): `sizeof(Early)` was 16 while
LLVM's `%Early = type {%Late, i8}` is 32 bytes. The same size function sizes
enum payload buffers, so `enum E { A(Early) }` got a buffer too small for the
value stored into it.

Each probe is checked against LLVM's own layout of the emitted IR, reusing
the oracle from test_sizeof_enum_field.py.
"""

import os
import re
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from test_sizeof_enum_field import _llvm_abi_sizes, _sizeof_constants

RITZ_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.integration

SOURCE = """\
struct Early
    late: Late
    k: i8

enum HoldsEarly
    A(Early)
    B

struct EnumFirst
    e: LateEnum
    t: i8

enum LateEnum
    P(Later)
    Q

struct Chain
    m: Mid
    z: i8

struct Mid
    l: Late
    y: i8

struct GenEarly
    b: Box<Late>
    k: i8

struct Box<T>
    v: T

struct Late
    a: i64
    b: i64
    c: i64

struct Later
    x: i64
    y: i64

fn sz_Early() -> i64
    return sizeof(Early)
fn sz_HoldsEarly() -> i64
    return sizeof(HoldsEarly)
fn sz_EnumFirst() -> i64
    return sizeof(EnumFirst)
fn sz_LateEnum() -> i64
    return sizeof(LateEnum)
fn sz_Chain() -> i64
    return sizeof(Chain)
fn sz_Mid() -> i64
    return sizeof(Mid)
fn sz_GenEarly() -> i64
    return sizeof(GenEarly)
fn sz_Late() -> i64
    return sizeof(Late)

fn main() -> i32
    0
"""

# Readable cross-check of the LLVM oracle.
EXPECTED = {
    "Early": 32,  # %Late (24) + i8, padded to 8
    "HoldsEarly": 40,  # { i8, [7 x i8] pad to Early's 8-align, [32 x i8] }
    "EnumFirst": 25,  # %LateEnum (24, 1-aligned) + i8
    "LateEnum": 24,  # { i8, [7 x i8], [16 x i8] }
    "Chain": 40,  # %Mid (32) + i8, padded to 8
    "Mid": 32,
    "GenEarly": 32,  # %Box$Late (24) + i8, padded to 8
    "Late": 24,
}


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sizeof_fwd_struct")
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


def test_enum_payload_buffer_holds_forward_struct(compiled):
    # HoldsEarly.A(Early): the payload buffer must hold all 32 bytes of Early.
    m = re.search(r'%"enum\.[^.]+\.HoldsEarly" = type \{(.*)\}', compiled)
    assert m, "HoldsEarly not emitted"
    arrays = [int(n) for n in re.findall(r"\[(\d+) x i8\]", m.group(1))]
    assert arrays and arrays[-1] >= 32, m.group(0)
