"""AGAST #4544: a `[[packed]]` struct's constant initialiser is packed.

THE DEFECT

ritz0 lowers a `[[packed]]` struct module-level initialiser as a packed
LLVM constant (`%T <{ ... }>`).  ritz1 emitted the struct *type* packed
(emit_one_struct_type writes `%T = type <{ ... }>` for a `[[packed]]`
struct) but the *value* through emit_const_struct_body, which wrote a bare
`{ ... }`.  ritz1 exited 0 and clang refused the IR with

    error: packed'ness of initializer and type don't match

for every fmt of initialiser that reaches that body:

  * a global struct (`var g: P = P { ... }`),
  * a const struct (`const C: P = P { ... }`),
  * a packed struct nested in another struct's literal,
  * an array of packed structs, global or const.

The fix branches on struct_is_packed in emit_const_struct_body exactly as
emit_one_struct_type does.  A non-packed struct still emits `{ ... }`; every
program returns 3 on success, and ritz0 is the oracle.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
# Build product, not a tracked file; see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

EFI_GUID = """\
[[packed]]
struct EfiGuid
    data1: u32
    data2: u16
    data3: u16
    data4: [8]u8

var guid: EfiGuid = EfiGuid { data1: 0x5B1B31A1, data2: 0x9562, data3: 0x11D2, data4: [0x8E, 0x3F, 0x00, 0xA0, 0xC9, 0x69, 0x72, 0x3B] }

pub fn main() -> i32
    if guid.data1 != 0x5B1B31A1
        return 10
    if guid.data4[7] != 0x3B
        return 11
    3
"""

CONST_PACKED = """\
[[packed]]
struct P
    a: u8
    b: u32

const C: P = P { a: 7, b: 0x11223344 }

pub fn main() -> i32
    if C.a != 7
        return 10
    if C.b != 0x11223344
        return 11
    3
"""

# A packed struct as a field value inside a non-packed outer struct's literal.
NESTED_PACKED = """\
[[packed]]
struct Inner
    a: u8
    b: u32

struct Outer
    head: u8
    inner: Inner
    tail: u8

var g: Outer = Outer { head: 1, inner: Inner { a: 2, b: 0x03040506 }, tail: 9 }

pub fn main() -> i32
    if g.head != 1
        return 10
    if g.inner.a != 2
        return 11
    if g.inner.b != 0x03040506
        return 12
    if g.tail != 9
        return 13
    3
"""

ARRAY_OF_PACKED = """\
[[packed]]
struct P
    a: u8
    b: u32

var arr: [2]P = [P { a: 1, b: 0x01020304 }, P { a: 2, b: 0x05060708 }]

pub fn main() -> i32
    if arr[0].a != 1
        return 10
    if arr[0].b != 0x01020304
        return 11
    if arr[1].a != 2
        return 12
    if arr[1].b != 0x05060708
        return 13
    3
"""

# The const-array path (emit_const_struct_literal -> emit_const_struct_body).
CONST_ARRAY = """\
[[packed]]
struct P
    a: u8
    b: u32

const T: [2]P = [P { a: 3, b: 0x0D0C0B0A }, P { a: 4, b: 0x01010101 }]

pub fn main() -> i32
    if T[0].a != 3
        return 10
    if T[0].b != 0x0D0C0B0A
        return 11
    if T[1].a != 4
        return 12
    if T[1].b != 0x01010101
        return 13
    3
"""

# Control: an unpacked struct keeps `{ ... }` (never `<{ ... }>`).
NON_PACKED = """\
struct S
    a: u8
    b: u32

var g: S = S { a: 5, b: 0x0A0B0C0D }

pub fn main() -> i32
    if g.a != 5
        return 10
    if g.b != 0x0A0B0C0D
        return 11
    3
"""

CASES = {
    "efi_guid": EFI_GUID,
    "const_packed": CONST_PACKED,
    "nested_packed": NESTED_PACKED,
    "array_of_packed": ARRAY_OF_PACKED,
    "const_array": CONST_ARRAY,
    "non_packed": NON_PACKED,
}

# Per case: the initialiser the IR must show, and how many times.  The
# pattern is anchored on the defined name, so it cannot match the packed
# `type <{ ... }>` declarations, only a constant written with a `<`.
PACKED_IR = {
    "efi_guid": (r"^@guid\s*=.*global %EfiGuid <\{", 1),
    "const_packed": (r"^@C\s*=.*constant %P <\{", 1),
    "nested_packed": (r"%Inner <\{", 1),
    "array_of_packed": (r"%P <\{", 2),
    "const_array": (r"%P <\{", 2),
}
UNPACKED_IR = r"^@g\s*=.*global %S \{"


def _compile(compiler: str, ritz1_bin, tmp_path: Path, name: str) -> tuple[Path, Path]:
    """Compile `name` with `compiler`; return the IR path and the work dir."""
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(CASES[name])
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        comp = subprocess.run(
            [str(ritz1_bin), str(src), "-o", str(ll)],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return ll, work


def _run(compiler: str, ritz1_bin, tmp_path: Path, name: str) -> int:
    ll, work = _compile(compiler, ritz1_bin, tmp_path, name)
    exe = work / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib", "-no-pie"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR clang rejects for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", None, tmp_path, name) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_packed_const_initialiser_runs(ritz1_bin, tmp_path, name):
    """AGAST #4544. Before the fix: clang's packed'ness mismatch."""
    assert _run("ritz1", ritz1_bin, tmp_path, name) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PACKED_IR))
def test_ritz1_packed_const_initialiser_is_packed_ir(ritz1_bin, tmp_path, name):
    """The initialiser uses `<{ ... }>`, as the type declaration does."""
    pattern, want = PACKED_IR[name]
    ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name)
    hits = re.findall(pattern, ll.read_text(), re.MULTILINE)
    assert len(hits) == want, (
        f"{name}: expected {want} packed initialiser(s) matching {pattern!r}, "
        f"got {len(hits)}:\n" + "\n".join(
            line for line in ll.read_text().splitlines() if "<{" in line
        )
    )


@pytest.mark.integration
def test_ritz1_unpacked_const_initialiser_stays_unpacked(ritz1_bin, tmp_path):
    """The control: a plain struct's constant must not gain a `<`."""
    ll, _ = _compile("ritz1", ritz1_bin, tmp_path, "non_packed")
    text = ll.read_text()
    assert re.search(UNPACKED_IR, text, re.MULTILINE), (
        "non-packed global lost its plain `{ ... }` initialiser"
    )
    assert "%S <{" not in text, "non-packed struct gained a packed initialiser"
