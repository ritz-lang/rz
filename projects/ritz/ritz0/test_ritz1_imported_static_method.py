"""Regression tests for AGAST #2568: ritz1 never declared a STATIC impl
method defined in an imported module.

THE DEFECT

`P.new(7)`, with `impl P` in an imported module, emitted
`call %P @P_new(i64 ...)` and no `declare`, so clang rejected the .ll with
"use of undefined value '@P_new'". The instance arm (`p.get()`) already
registered the `Type_method` extern when the method's FnDef came from an
imported impl (is_local == 0, AGAST #1518); the static arm
(emit_expr_method's `Type.method` branch) never did.

THE TESTS

Each program is built as a package under ritz0 and ritz1; ritz0 is the
oracle. The imported impl has static methods with a struct return, an sret
struct return, an i64 return and an i32 return; one that main calls and the
imported module also calls itself (`make_p`), one nobody calls, and an
instance method as the control. Both `import pt` and `import pt { ... }`.
The IR tests check each called static method is declared exactly once in
main.ll, the uncalled one isn't, and pt.ll keeps a single `define` with no
`declare` beside it.
"""

import os
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import RITZ_ROOT

PT = """\
pub struct P
    x: i64

# Over ritz1's SRET_MIN_BYTES (256): returned through `ptr sret(%Huge)`.
pub struct Huge
    pad: [40]i64
    tag: i64

impl P
    pub fn new(x: i64) -> P
        P { x: x }

    pub fn seven() -> i64
        7

    pub fn half(k: i32) -> i32
        k / 2

    pub fn huge(t: i64) -> Huge
        var h: Huge
        h.pad[39] = t
        h.tag = t
        h

    pub fn unused() -> i64
        3

    pub fn get(self: @P) -> i64
        self.x

# Calls the static method inside its own module too.
pub fn make_p(x: i64) -> P
    P.new(x * 2)
"""

MAIN_BODY = """\
pub fn main() -> i32
    let p: P = P.new(7)
    let q: P = make_p(5)
    let h: Huge = P.huge(3)
    var r: i64 = p.get() + P.seven() * 10 + q.x * 100 + h.tag + h.pad[39]
    r = r + (P.half(8) as i64) * 1000
    return (r % 251) as i32
"""

MAIN_PLAIN = "import pt\n\n" + MAIN_BODY
MAIN_SELECTIVE = "import pt { P, Huge, make_p }\n\n" + MAIN_BODY

# Instance method only: worked before #2568, kept as the control.
MAIN_INSTANCE = """\
import pt

pub fn main() -> i32
    let p: P = P { x: 7 }
    return p.get() as i32
"""

# 7 + 70 + 1000 + 3 + 3 + 4000 = 5083; 5083 % 251 = 63.
CASES = {
    "plain_import": ({"main.ritz": MAIN_PLAIN, "pt.ritz": PT}, 63),
    "selective_import": ({"main.ritz": MAIN_SELECTIVE, "pt.ritz": PT}, 63),
    "instance_control": ({"main.ritz": MAIN_INSTANCE, "pt.ritz": PT}, 7),
}


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
    # AGAST #2793: cached build; ritzlib objects come from the session's
    # content-addressed store, the per-project index stays in the package.
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT),
               RITZ_BUILD_CACHE_DIR=str(pkg / ".build-cache"))
    proc = subprocess.run(
        [
            "python3",
            str(RITZ_ROOT / "build.py"),
            "build",
            str(pkg),
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


@pytest.mark.integration
@pytest.mark.parametrize("case", sorted(CASES))
def test_imported_static_method_matches_ritz0(ritz1_bin, tmp_path, case):
    files, expected = CASES[case]
    want = _build_and_run("ritz0", tmp_path, case, files)
    assert want == expected, f"ritz0 oracle drifted for {case}: {want}"
    got = _build_and_run("ritz1", tmp_path, case, files)
    assert got == want, f"{case}: ritz1 exit {got}, ritz0 exit {want}"


def _ritz1_ll(ritz1_bin, tmp_path: Path, src_name: str) -> list[str]:
    """Compile tmp_path/<src_name> with ritz1 alone; return the .ll's lines."""
    ll = tmp_path / (src_name + ".ll")
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    comp = subprocess.run(
        [str(ritz1_bin), str(tmp_path / src_name), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0, comp.stderr[-2000:]
    return ll.read_text().splitlines()


def _declared(lines: list[str], sym: str) -> list[str]:
    return [ln for ln in lines if ln.startswith("declare") and f"@{sym}(" in ln]


def _defined(lines: list[str], sym: str) -> list[str]:
    return [ln for ln in lines if ln.startswith("define") and f"@{sym}(" in ln]


@pytest.mark.integration
@pytest.mark.parametrize(
    "main_src", [MAIN_PLAIN, MAIN_SELECTIVE], ids=["plain", "selective"]
)
def test_importer_declares_each_called_static_method_once(
    ritz1_bin, tmp_path, main_src
):
    (tmp_path / "pt.ritz").write_text(PT)
    (tmp_path / "main.ritz").write_text(main_src)
    lines = _ritz1_ll(ritz1_bin, tmp_path, "main.ritz")
    for sym in ("P_new", "P_seven", "P_half", "P_huge", "P_get"):
        assert len(_declared(lines, sym)) == 1, f"{sym}: {_declared(lines, sym)}"
        assert not _defined(lines, sym), f"{sym} defined in the importer"
    assert _declared(lines, "P_new")[0].startswith("declare %P @P_new(")
    assert _declared(lines, "P_seven")[0].startswith("declare i64 @P_seven(")
    assert _declared(lines, "P_half")[0].startswith("declare i32 @P_half(")
    assert _declared(lines, "P_huge")[0].startswith("declare void @P_huge(")
    assert not _declared(lines, "P_unused"), "an uncalled static method was declared"


@pytest.mark.integration
def test_owning_module_defines_static_method_without_declare(ritz1_bin, tmp_path):
    """pt.ll calls P.new itself (make_p): it must stay one `define`, no
    `declare` beside it (LLVM: invalid redefinition)."""
    (tmp_path / "pt.ritz").write_text(PT)
    lines = _ritz1_ll(ritz1_bin, tmp_path, "pt.ritz")
    for sym in ("P_new", "P_seven", "P_half", "P_huge", "P_unused", "P_get"):
        assert len(_defined(lines, sym)) == 1, f"{sym} not defined once"
        assert not _declared(lines, sym), f"{sym} declared beside its define"
