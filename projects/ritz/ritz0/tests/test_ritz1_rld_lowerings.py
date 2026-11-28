#!/usr/bin/env python3
"""Three ritz1 lowerings rld's sources exposed (AGAST #4809), one table.

- `v[i] == E.X` on a `Vec<E>` / `Span<E>` of a fieldless enum: ritz1 reads
  `v[i]` as `*(v.data + i)`, which loads a `%E`, but the `==` probe
  (unit_enum_expr_name) named no enum for it, so it emitted
  `icmp ne i64 %<%E>` and clang refused it.  rld: `img.relax[r] != Relax.Keep`.
- A call in a binding's own initialiser: a binding is in scope from the
  binding on (LANGUAGE_SPEC 4.3), but ritz1 registers the local first, so
  `let size: i64 = size(3)` called the uninitialised slot, a silent segfault.
  rld: `let phnum: i64 = phnum(l, img)`.
- `@T` of a module `const T: [N]X` into a `Span<X>` parameter passed the
  address as an i64 where the `%Span$X` goes.  rld's test_link.ritz:
  `emit(@&obj, text, @START)`.

One test, so the suite's case cap holds (docs/TESTING.md, "What a ritz0
pytest case costs"): every row on ritz0, ritz1 and ritz1_selfhosted, each
failing row named.  A row with an exit code links and runs; a Vec / Span row
can't link without ritzlib's allocator, so clang accepting its IR is the
check, and rld's own tests (built under each compiler) check the values.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

_PRELUDE = ("import ritzlib.gvec { Vec, vec_new }\nimport ritzlib.span { Span, span_from_vec }\n"
            "enum Kind\n    Keep\n    Near\n    Far\n")

_SUM = ("fn total(s: Span<u8>) -> i32\n    var t: i32 = 0\n    for i in 0..s.len\n"
        "        t += s[i] as i32\n    t * 10 + s.len as i32\n")

# name: (source, exit code, or None for compile-only).
PROGRAMS = {
    # A Vec local: `!=` and `==` against a variant, either side.
    "enum_vec_local": (_PRELUDE + "fn main() -> i32\n    var v: Vec<Kind> = vec_new<Kind>()\n"
                  "    v.push(Kind.Near)\n    v.push(Kind.Far)\n    var n: i32 = 0\n"
                  "    if v[0] != Kind.Keep\n        n += 1\n    if v[1] == Kind.Far\n        n += 2\n"
                  "    if Kind.Near == v[1]\n        n += 4\n    n\n", None),
    # rld's shape: a Vec field through a mutable reference.
    "enum_vec_field_through_ref": (_PRELUDE + "struct Img\n    kinds: Vec<Kind>\n"
                              "fn count(img: @&Img) -> i32\n    var n: i32 = 0\n"
                              "    for r in 0..img.kinds.len\n        if img.kinds[r] != Kind.Keep\n"
                              "            n += 1\n    n\n"
                              "fn main() -> i32\n    var img: Img = Img { kinds: vec_new<Kind>() }\n"
                              "    img.kinds.push(Kind.Keep)\n    img.kinds.push(Kind.Far)\n"
                              "    img.kinds.push(Kind.Near)\n    count(@&img)\n", None),
    "enum_span_local": (_PRELUDE + "fn main() -> i32\n    var v: Vec<Kind> = vec_new<Kind>()\n"
                   "    v.push(Kind.Keep)\n    v.push(Kind.Far)\n"
                   "    let s: Span<Kind> = span_from_vec<Kind>(@v)\n"
                   "    if s[1] == Kind.Far and s[0] != Kind.Near then 5 else 1\n", None),
    "init_let": ("fn size(n: i64) -> i64\n    n + 4\nfn main() -> i32\n"
            "    let size: i64 = size(3)\n    size as i32\n", 7),
    "init_var": ("fn size(n: i64) -> i64\n    n + 4\nfn main() -> i32\n"
            "    var size: i64 = size(3)\n    size += 1\n    size as i32\n", 8),
    # An inner binding's initialiser inside the outer's: after it, the outer
    # one's call still names the fn.
    "init_nested": ("fn size(n: i64) -> i64\n    n + 4\nfn twice(n: i64) -> i64\n    n * 2\n"
               "fn main() -> i32\n    let size: i64 = if true\n"
               "        let twice: i64 = twice(1)\n        size(twice)\n    else\n        0\n"
               "    size as i32\n", 6),
    # Once bound, a call of the non-fn local is still refused (#2407).
    "const_span_u8": ("const T: [4]u8 = [1, 2, 3, 4]\n" + _SUM +
           "fn main() -> i32\n    total(@T)\n", 104),
    # A second const, so the span names its own global.
    "const_span_two": ("const A: [2]u8 = [5, 6]\nconst B: [3]u8 = [1, 1, 1]\n" + _SUM +
                   "fn main() -> i32\n    total(@A) - total(@B)\n", 79),
}

# Once bound, a call of the non-fn local is still refused (#2407).
REFUSED = ("fn size() -> i32\n    7\nfn main() -> i32\n"
           "    let size: i32 = 3\n    size()\n")
REFUSAL = "'size' is a local, not a fn: it can't be called"


def _compile(compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300), ll
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)],
                          cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


def _row(compiler, tmp_path, source, code):
    """What is wrong with one row, or None."""
    proc, ll = _compile(compiler, tmp_path, source)
    if proc.returncode != 0 or not ll.exists():
        return f"compile: {(proc.stdout + proc.stderr)[-600:]}"
    if code is None:
        cc = subprocess.run(["clang", "-w", "-c", str(ll), "-o", str(tmp_path / "unit.o")],
                            capture_output=True, text=True, timeout=120)
        return None if cc.returncode == 0 else f"clang: {cc.stderr[-600:]}"
    exe = tmp_path / "unit"
    # ritz0 emits its own `_start`; ritz1 links the runtime's.
    start = [] if compiler == "ritz0" else [str(RITZ_START)]
    link = fast_link.clang(["clang", "-w", str(ll), *start, "-o", str(exe), "-nostdlib"],
                          capture_output=True, text=True)
    if link.returncode != 0:
        return f"link: {link.stderr[-600:]}"
    got = subprocess.run([str(exe)], timeout=60).returncode
    return None if got == code else f"exit {got}, want {code}"


@pytest.mark.integration
def test_rld_exposed_lowerings(request, tmp_path):
    request.getfixturevalue("ritz1_bin")
    failures = []
    for compiler in COMPILERS:
        for name, (source, code) in sorted(PROGRAMS.items()):
            row = tmp_path / f"{compiler}-{name}"
            row.mkdir()
            why = _row(compiler, row, source, code)
            if why is not None:
                failures.append(f"{compiler}, {name}: {why}")
    refused = tmp_path / "refused"
    refused.mkdir()
    proc, _ = _compile("ritz1", refused, REFUSED)
    if proc.returncode == 0 or REFUSAL not in proc.stdout + proc.stderr:
        failures.append("ritz1, refused: a call of a bound non-fn local compiled")
    assert not failures, "\n".join(failures)
