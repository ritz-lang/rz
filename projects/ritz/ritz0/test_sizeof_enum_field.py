#!/usr/bin/env python3
"""sizeof must equal the LLVM ABI size of the type ritz0 emits (AGAST #1923).

ritz0 sized every enum-typed field as 8 bytes / 8-aligned (the unknown-type
fallback of `_ritz_type_size_and_align`), but emits the enum as an all-i8
struct `{ i8 tag, [P x i8], [N x i8] }` -- 1-aligned, `1 + P + N` bytes. So

    enum Mix
        Tiny(u8)
        Big
            a: i64
            b: i64
            c: i64
    struct Holder
        m: Mix
        after: i64

was emitted as `{ %Mix, i64 }` (40 bytes) while `sizeof(Holder)` said 16, and
`malloc(sizeof(Holder))` under-allocated by 24 bytes. The same fallback sized
an enum nested in another enum's payload at 8 bytes, so `Wrap.W(Mix)` got an
8-byte payload buffer for a 32-byte value.

Each probe below is checked against LLVM's own layout of the emitted IR
(llvmlite's target data), not against hand-computed numbers, so the test
pins "sizeof agrees with the type we emit" rather than any one layout.
"""

import os
import re
from pathlib import Path

import llvmlite.binding as llvm
import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.integration

# x86_64-unknown-linux-gnu data layout.
DATA_LAYOUT = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"

SOURCE = """\
enum Mix
    Tiny(u8)
    Big
        a: i64
        b: i64
        c: i64

struct Holder
    m: Mix
    after: i64

enum Dir
    North
    South

struct Heading
    d: Dir
    n: i32

enum Wrap
    W(Mix)
    Z

struct WrapHolder
    w: Wrap
    tail: i8

struct OptHolder
    o: Option<i64>
    k: i8

enum Small
    S(u8)
    T

struct SmallHolder
    s: Small
    x: i16

fn sz_Holder() -> i64
    return sizeof(Holder)
fn sz_Mix() -> i64
    return sizeof(Mix)
fn sz_Heading() -> i64
    return sizeof(Heading)
fn sz_Dir() -> i64
    return sizeof(Dir)
fn sz_Wrap() -> i64
    return sizeof(Wrap)
fn sz_WrapHolder() -> i64
    return sizeof(WrapHolder)
fn sz_OptHolder() -> i64
    return sizeof(OptHolder)
fn sz_Small() -> i64
    return sizeof(Small)
fn sz_SmallHolder() -> i64
    return sizeof(SmallHolder)

fn main() -> i32
    0
"""

# The ticket's numbers, as a readable cross-check of the LLVM oracle.
EXPECTED = {
    "Holder": 40,  # %Mix (32) + i64
    "Mix": 32,  # { i8, [7 x i8], [24 x i8] }
    "Heading": 8,  # %Dir (1) + pad 3 + i32
    "Dir": 1,  # { i8 }
    "Wrap": 33,  # { i8, [32 x i8] } -- Mix is 1-aligned
    "WrapHolder": 34,
    "OptHolder": 17,  # Option<i64> (16, all-i8 so 1-aligned) + i8
    "Small": 2,  # { i8, [1 x i8] }
    "SmallHolder": 4,  # %Small (2) + i16
}


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sizeof_enum")
    src = tmp / "unit.ritz"
    src.write_text(SOURCE)
    out = tmp / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    res = run_ritz0([str(src), "-o", str(out)], env=env)
    assert res.returncode == 0, res.stderr
    return out.read_text()


def _sizeof_constants(ir_text):
    """name -> the constant `sz_<name>` returns."""
    found = {}
    for m in re.finditer(r'define [^@]*@"?sz_(\w+)"?\(.*?\{(.*?)\n\}', ir_text, re.S):
        ret = re.search(r"ret i64 (\d+)", m.group(2))
        assert ret, f"sz_{m.group(1)} does not return a constant"
        found[m.group(1)] = int(ret.group(1))
    return found


def _llvm_abi_sizes(ir_text):
    """Ritz type name -> LLVM ABI size of the identified type ritz0 emits."""
    # A type nothing references is invisible to llvmlite's module API, so
    # anchor each one with an external global and size its value type.
    names = re.findall(r'^(%"(?:struct|enum)\.[^.]+\.(\w+)") = type', ir_text, re.M)
    anchors = "".join(f"@__sz_probe_{n} = external global {t}\n" for t, n in names)
    mod = llvm.parse_assembly(ir_text + "\n" + anchors)
    td = llvm.create_target_data(DATA_LAYOUT)
    return {
        n: td.get_abi_size(mod.get_global_variable(f"__sz_probe_{n}").global_value_type)
        for _, n in names
    }


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


def test_nested_enum_payload_buffer_holds_the_whole_enum(compiled):
    # Wrap.W(Mix): the payload buffer must be at least sizeof(Mix), or
    # constructing W(m) stores 32 bytes into an 8-byte buffer.
    m = re.search(r'%"enum\.[^.]+\.Wrap" = type \{(.*)\}', compiled)
    assert m, "Wrap not emitted"
    arrays = [int(n) for n in re.findall(r"\[(\d+) x i8\]", m.group(1))]
    assert arrays and arrays[-1] >= 32, m.group(0)
