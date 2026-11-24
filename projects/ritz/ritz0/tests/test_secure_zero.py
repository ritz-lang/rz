"""AGAST #1864: ritzlib `secure_zero` survives dead-store elimination.

Zeroing a secret the program never reads again is a dead store, and -O2
deletes it (or LTO does, once the zeroing fn is inlined across modules).
`secure_zero` (ritzlib/memory.ritz, LANGUAGE_SPEC §18.4) writes every byte
with `volatile_store`, which the optimiser never removes.

Each test runs on ritz0, ritz1 and ritz1_selfhosted:

* the zeroing fn emits volatile i8 and i64 stores;
* after `clang -O2` the volatile stores are still in the fn that wipes a dead
  local key, while a plain zeroing loop in the same position is gone (the
  control: proves the pipeline really does eliminate dead stores);
* it zeroes exactly [p, p+n) for every head alignment and length.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import fast_link
import pytest
import test_ir
from test_kernel_features import COMPILERS, RITZ_ROOT, RITZ_START, _ir

pytestmark = pytest.mark.integration

# derive(seed) fills a 37-byte local key from `seed` (so nothing folds), sums
# it, then wipes it. 37 is odd, so the wipe has a byte head or tail as well as
# aligned words. The key is dead after the wipe: exactly the cryptosec shape.
DEAD_KEY = """\
import ritzlib.memory
import ritzlib.span

[[noinline]]
fn derive(seed: u8) -> i32
    var key: [37]u8
    for i in 0..37
        key[i] = seed + i as u8
    var sum: i32 = 0
    for i in 0..37
        sum = sum + key[i] as i32
    {wipe}
    sum

fn main() -> i32
    derive(3) & 0x7f
"""

SECURE_WIPE = "secure_zero(@key[0], 37)"
# AGAST #4638: the Span method cryptosec's key wipes use. Its volatile stores
# are memory.secure_zero's, reached through a generic method instantiated in
# the caller's module, so -O2 sees the whole chain.
SPAN_WIPE = "var ks: Span<u8> = span_from_ptr<u8>(@key[0], 37)\n    ks.secure_zero()"
PLAIN_WIPE = "for j in 0..37\n        key[j] = 0"


# Each compiler emits one module per source; an imported fn is a `declare`.
# ritzlib.memory and what it imports, compiled alongside the program.
RITZLIB_MODULES = ("memory", "str", "sys", "fmt/digits")


def _llvm_tool(name):
    """`name` from PATH, else beside the real clang (/usr/lib/llvm-N/bin):
    Ubuntu ships llvm-link only under a suffixed name on PATH."""
    found = shutil.which(name)
    if found:
        return found
    sibling = Path(os.path.realpath(shutil.which("clang"))).parent / name
    # Never skip (#1327): clang's own LLVM bin dir has it.
    assert sibling.exists(), f"no {name} on PATH or at {sibling}"
    return str(sibling)


def _modules(compiler, tmp_path, src, name):
    """The program's .ll plus one .ll per ritzlib module it needs."""
    lls = [_ir(compiler, tmp_path, src, name)]
    for mod in RITZLIB_MODULES:
        lls.append(_ir(compiler, tmp_path, (RITZ_ROOT / "ritzlib" / f"{mod}.ritz").read_text(),
                       f"ritzlib_{mod.replace('/', '_')}"))
    return lls


def _o2(compiler, tmp_path, src, name):
    """Link the program with ritzlib into one module, as LTO does, and -O2 it:
    secure_zero is inlined into its caller, where a plain wipe would be dead."""
    linked = tmp_path / f"{name}_{compiler}.linked.ll"
    proc = subprocess.run([_llvm_tool("llvm-link"), "-S", "-o", str(linked),
                           *map(str, _modules(compiler, tmp_path, src, name))],
                          capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"{compiler}: llvm-link failed:\n{proc.stderr[-3000:]}"
    out = tmp_path / f"{name}_{compiler}.O2.ll"
    proc = subprocess.run(["clang", "-Wno-override-module", "-O2", "-S", "-emit-llvm",
                           str(linked), "-o", str(out)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"{compiler}: clang -O2 failed:\n{proc.stderr[-3000:]}"
    return out.read_text()


def _fn_body(ir, name):
    """The text of `define ... @name(...) { ... }` in `ir`.  `name` is the
    Ritz name; a private fn's symbol carries its file (`derive__1a2b3c4d`,
    AGAST #1858/#4356), which test_ir.symbol accepts."""
    m = re.search(rf"^define [^\n]*{test_ir.symbol(name)}\(.*?^}}",
                  ir, re.MULTILINE | re.DOTALL)
    assert m, f"no define for {name}:\n{ir[:3000]}"
    return m.group(0)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_secure_zero_emits_volatile_stores(compiler, tmp_path):
    lib = RITZ_ROOT / "ritzlib" / "memory.ritz"
    ir = _ir(compiler, tmp_path, lib.read_text(), "ritzlib_memory").read_text()
    body = _fn_body(ir, "secure_zero")
    assert re.search(r"store volatile i8 ", body), f"{compiler}: no volatile byte store"
    assert re.search(r"store volatile i64 ", body), f"{compiler}: no volatile word store"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_secure_zero_survives_O2(compiler, tmp_path):
    secure = _o2(compiler, tmp_path, DEAD_KEY.replace("{wipe}", SECURE_WIPE), "sz")
    body = _fn_body(secure, "derive")
    # Inlined (volatile stores in derive) or not (derive still calls it and
    # its body keeps them): either way the wipe reaches memory.
    if re.search(rf"call [^\n]*{test_ir.symbol('secure_zero')}\(", body):
        body = _fn_body(secure, "secure_zero")
    assert re.search(r"store volatile i8 ", body), f"{compiler}: byte wipe elided at -O2:\n{body}"
    assert re.search(r"store volatile i64 ", body), f"{compiler}: word wipe elided at -O2:\n{body}"
    # Its own -O2 body: locals live in registers, so every store left is a
    # write to dst, and each must be volatile. A plain one in the head, word
    # or tail loop is a write that DSE deletes once inlined beside a dead
    # buffer, as in derive above.
    own = _fn_body(secure, "secure_zero")
    plain = [ln for ln in own.splitlines()
             if re.search(r"\bstore\b", ln) and "store volatile" not in ln]
    assert not plain and "memset" not in own, (
        f"{compiler}: secure_zero has a non-volatile write at -O2:\n{own}")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_span_secure_zero_survives_O2(compiler, tmp_path):
    """`key.secure_zero()` on a Span wipes a dead key as secure_zero does:
    the method must not fall back to plain stores (or Span.zero's memset)."""
    ir = _o2(compiler, tmp_path, DEAD_KEY.replace("{wipe}", SPAN_WIPE), "spansz")
    body = _fn_body(ir, "derive")
    # Inlined, or behind the method and/or secure_zero: follow the calls.
    m = re.search(r"call [^\n]*@(\S*Span\S*secure_zero\S*)\(", body)
    if m:
        body = _fn_body(ir, m.group(1))
    if re.search(rf"call [^\n]*{test_ir.symbol('secure_zero')}\(", body):
        body = _fn_body(ir, "secure_zero")
    assert re.search(r"store volatile i8 ", body), f"{compiler}: Span wipe elided at -O2:\n{body}"
    assert re.search(r"store volatile i64 ", body), f"{compiler}: Span wipe elided at -O2:\n{body}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_plain_wipe_is_elided_at_O2(compiler, tmp_path):
    """Control: the same wipe as plain stores is deleted, so the test above
    is measuring something."""
    plain = _o2(compiler, tmp_path, DEAD_KEY.replace("{wipe}", PLAIN_WIPE), "plain")
    body = _fn_body(plain, "derive")
    # The wipe is stores of zero; those must be gone.  Since LARB R63 the
    # sum loop's `+` carries an overflow guard, so LLVM no longer folds the
    # loop away and the key's initialising stores (3..39) stay -- they are
    # not the wipe, and their presence does not weaken the control.
    assert not re.search(
        r"store (i8 0\b|<[^>]*> zeroinitializer|zeroinitializer)|memset", body), (
        f"{compiler}: -O2 kept the plain wipe; the DSE control no longer holds:\n{body}")


# Fill 64 bytes with 0xAA, secure_zero [off, off+len) for every head offset
# 0..8 and length 0..24, and check the bytes inside are 0 and outside 0xAA.
EXACT = """\
import ritzlib.memory

fn main() -> i32
    var buf: [64]u64
    let base: *u8 = @buf[0] as *u8
    for off in 0..9
        for len in 0..25
            for k in 0..64
                *(base + k) = 0xAA
            secure_zero(base + off, len)
            for k in 0..64
                let inside: bool = k >= off and k < off + len
                let b: u8 = *(base + k)
                if inside and b != 0
                    return 1
                if not inside and b != 0xAA
                    return 2
    42
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_secure_zero_exact_range(compiler, tmp_path):
    objs = [str(ll) for ll in _modules(compiler, tmp_path, EXACT, "exact")]
    if compiler != "ritz0":
        objs.insert(0, str(RITZ_START))
    exe = tmp_path / f"exact_{compiler}"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                            "-nostdlib", "-no-pie"], capture_output=True, text=True, check=False)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    assert subprocess.run([str(exe)], timeout=60, check=False).returncode == 42
