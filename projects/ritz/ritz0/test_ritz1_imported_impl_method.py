"""Regression tests for AGAST #1518: ritz1 never declared an impl method
defined in an imported module.

THE DEFECT

The method-call emitter (emitter_expr_call.ritz) registered the
`Type_method` extern only when it could NOT find the method's FnDef
(`if mfn == null add_method_extern`). It assumed a found method is defined
in this .ll. But since #194 an imported impl method is in the module's impl
table with is_local == 0 and its body is emitted by the file that owns it,
so the call site referenced a symbol that was neither defined nor declared:
clang "use of undefined value '@Sq_area'".

It hit every imported impl: a user module's `impl Sq`, ritzlib's
`impl HashMapI64`, `impl Socket` (examples/tier5_async/50_http).

THE TESTS

Each program is built as a package (build.py compiles and links every
imported module) under ritz0 and ritz1; ritz0 is the oracle. The imported
methods cover each return shape the call site spells differently: i64, i32,
bool, void, a struct returned by value, a >256-byte struct returned via sret and passed byval, plus
`@` / `@&` reference receivers (HashMapI64) and i32 params.
"""

import os
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import RITZ_ROOT

# The ticket's two-file repro.
SHAPE_SQ = """\
pub struct Sq
    a: i64

impl Sq
    fn area(self: *Sq) -> i64
        return 9
"""

MAIN_SQ = """\
import shape

pub fn main() -> i32
    var s: Sq = Sq { a: 3 }
    return s.area() as i32
"""

# One imported impl with every return shape.
SHAPE_ALL = """\
pub struct Pt
    x: i64
    y: i64

pub struct Big
    a: i64
    b: i64
    c: i64
    d: i64
    e: i64

# Over ritz1's SRET_MIN_BYTES (256): returned through `ptr sret(%Huge)`.
pub struct Huge
    pad: [40]i64
    tag: i64

impl Pt
    fn sum(self: *Pt) -> i64
        return self.x + self.y

    fn narrow(self: *Pt, k: i32) -> i32
        return self.x as i32 * k

    fn is_origin(self: *Pt) -> bool
        return self.x == 0 and self.y == 0

    fn bump(self: *Pt, by: i64)
        self.x = self.x + by

    fn swapped(self: *Pt) -> Pt
        return Pt { x: self.y, y: self.x }

    fn big(self: *Pt) -> Big
        return Big { a: self.x, b: self.y, c: 1, d: 2, e: 3 }

    fn huge(self: *Pt) -> Huge
        var h: Huge
        h.pad[39] = self.y
        h.tag = 4
        return h

    fn weigh(self: *Pt, h: Huge) -> i64
        return h.tag + h.pad[39] + self.x
"""

MAIN_ALL = """\
import shape

pub fn main() -> i32
    var p: Pt = Pt { x: 2, y: 5 }
    p.bump(1)
    let q: Pt = p.swapped()
    let g: Big = p.big()
    let h: Huge = p.huge()
    var r: i64 = p.sum() + q.x * 10 + g.e * 100 + h.tag * 7 + h.pad[39] * 11
    r = r + (p.narrow(3) as i64) * 1000
    r = r + p.weigh(h) * 13
    if p.is_origin()
        r = 0
    return (r % 251) as i32
"""

# The ticket's ritzlib addendum: the HashMapI64 method form.
MAIN_HASHMAP = """\
import ritzlib.hashmap

pub fn main() -> i32
    var m: HashMapI64 = hashmap_i64_new()
    m.insert(1000, 1)
    m.insert(1000, 2)
    m.insert(7, 3)
    var r: i64 = m.get(1000)
    r = r + m.contains(1000) as i64 * 10
    r = r + m.remove(7) as i64 * 20
    r = r + m.len() * 40
    r = r + m.is_empty() as i64 * 80
    return (r + m.cap()) as i32
"""

# 50_http's shape: ritzlib.net Socket methods, incl. a struct-returning one.
# accept() would block, so it sits on a branch that never runs; the build is
# what was broken.
MAIN_SOCKET = """\
import ritzlib.net

pub fn main() -> i32
    var s: Socket = socket_tcp()
    if s.valid() == 0
        return 1
    let r: i32 = s.set_reuseaddr()
    if s.fd < -1000
        var c: Socket = s.accept()
        c.close()
    s.close()
    return 40 + r
"""


def _build_and_run(
    compiler: str, tmp_path: Path, name: str, files: dict[str, str]
) -> int:
    """Build a package whose src/ holds `files`, run it, return its exit code."""
    pkg = tmp_path / f"{name}_{compiler}"
    (pkg / "src").mkdir(parents=True)
    for fname, text in files.items():
        (pkg / "src" / fname).write_text(text)
    (pkg / "ritz.toml").write_text(
        f'[package]\nname = "{name}"\nversion = "0.1.0"\n\n'
        '[build]\ntarget = "x86_64-linux"\n'
    )
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [
            "python3",
            str(RITZ_ROOT / "build.py"),
            "build",
            str(pkg),
            "--no-cache",
            "--compiler",
            compiler,
        ],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    exe = pkg / "build" / "debug" / name
    assert proc.returncode == 0 and exe.exists(), (
        f"{compiler} failed to build {name}:\n"
        f"{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


CASES = {
    "two_file_repro": ({"main.ritz": MAIN_SQ, "shape.ritz": SHAPE_SQ}, 9),
    "every_return_shape": ({"main.ritz": MAIN_ALL, "shape.ritz": SHAPE_ALL}, None),
    "ritzlib_hashmap": ({"main.ritz": MAIN_HASHMAP}, None),
    "ritzlib_socket": ({"main.ritz": MAIN_SOCKET}, None),
}


@pytest.mark.integration
@pytest.mark.parametrize("case", sorted(CASES))
def test_imported_impl_method_matches_ritz0(ritz1_bin, tmp_path, case):
    files, expected = CASES[case]
    want = _build_and_run("ritz0", tmp_path, case, files)
    if expected is not None:
        assert want == expected, f"ritz0 oracle drifted for {case}: {want}"
    got = _build_and_run("ritz1", tmp_path, case, files)
    assert got == want, f"{case}: ritz1 exit {got}, ritz0 exit {want}"


@pytest.mark.integration
def test_local_impl_method_is_not_also_declared(ritz1_bin, tmp_path):
    """The method defined in THIS file must stay a single `define` with no
    `declare` beside it (LLVM: invalid redefinition)."""
    src = tmp_path / "local.ritz"
    src.write_text(SHAPE_SQ + "\n" + MAIN_SQ.replace("import shape\n", ""))
    ll = tmp_path / "local.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    assert "@Sq_area(" in ir
    assert not any(
        line.startswith("declare") and "@Sq_area(" in line for line in ir.splitlines()
    ), "local impl method was also declared"


@pytest.mark.integration
def test_imported_method_declare_matches_signature(ritz1_bin, tmp_path):
    """Each imported method gets exactly one `declare`, spelled from its FnDef
    the way a free function's is: sret methods return void, a byval param
    gets the concrete signature (#1739), i32 / struct returns keep their type.
    """
    (tmp_path / "shape.ritz").write_text(SHAPE_ALL)
    src = tmp_path / "main.ritz"
    src.write_text(MAIN_ALL)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    comp = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0, comp.stderr[-2000:]
    declares = {
        line.split("@", 1)[1].split("(", 1)[0]: line
        for line in ll.read_text().splitlines()
        if line.startswith("declare") and "@Pt_" in line
    }
    assert sorted(declares) == sorted(
        f"Pt_{m}"
        for m in (
            "sum",
            "narrow",
            "is_origin",
            "bump",
            "swapped",
            "big",
            "huge",
            "weigh",
        )
    )
    assert declares["Pt_huge"].startswith("declare void @Pt_huge(")
    assert declares["Pt_weigh"] == (
        "declare i64 @Pt_weigh(ptr, ptr byval(%Huge) align 8)"
    )
    assert declares["Pt_narrow"].startswith("declare i32 @Pt_narrow(")
    assert declares["Pt_swapped"].startswith("declare %Pt @Pt_swapped(")
    assert declares["Pt_bump"].startswith("declare void @Pt_bump(")
