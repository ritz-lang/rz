"""A fn name defined twice in one import closure is an error (#2148).

Imported names share one flat namespace (LANGUAGE_SPEC §15.3), private or
not.  ritz0's import resolver used to keep the *last* ungated definition of
a fn name ("last one wins": a later import, or the main file, silently
replaced an earlier one, so callers inside the earlier module ran the wrong
body), and ritz1 merged both, emitting the main file's as `weak_odr` so the
linker picked one.  Both now reject it with

    Conflicting function definition for 'helper': defined in both A and B

A being the earlier definition in ritz0's registration order (imports before
the file importing them, the main file last).  Every case runs ritz0 and both
ritz1 binaries.

Rejected: import vs import (private or `pub`, differing or even identical
bodies), main file vs import (the rzsh tests' shadowed `println`), nested
imports (the diagnostic names the file that defined the fn), two in one file,
and a user fn named like a generated `E__from`.

Accepted, and still running correctly: a diamond import (one module reached
twice is registered once), the same name as `extern fn` in two modules, a
`[[target_os]]` fn beside an ungated one (never compared, as for consts), and
identical `enum E: u8` in two modules that import ritzlib.option (each
generates `E__from`; the enums are already checked identical).
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PREFIX = "Conflicting function definition for "


def _write(tmp_path, files):
    for name, text in files.items():
        (tmp_path / f"{name}.ritz").write_text(text)


def _compile(compiler, tmp_path, name):
    src = tmp_path / f"{name}.ritz"
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll), "--no-runtime"], cwd=tmp_path,
                         env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)],
                              cwd=tmp_path, env=env, capture_output=True,
                              text=True, timeout=300)
    return proc, ll


def _conflict(tmp_path, name, first, second):
    return (f"{PREFIX}'{name}': defined in both "
            f"{tmp_path / (first + '.ritz')} and {tmp_path / (second + '.ritz')}")


def _assert_rejected(compiler, tmp_path, diag, main="t"):
    proc, _ = _compile(compiler, tmp_path, main)
    out = proc.stderr + proc.stdout
    assert proc.returncode != 0, f"{compiler} accepted a duplicate fn:\n{out}"
    assert diag in out, f"{compiler}: wrong diagnostic, want {diag!r}:\n{out}"


def _run(compiler, tmp_path, names):
    """Compile each file to its own object, link, run; return the exit code."""
    objs = [str(RITZ_START)]
    for name in names:
        proc, ll = _compile(compiler, tmp_path, name)
        out = proc.stderr + proc.stdout
        assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected {name}:\n{out}"
        assert PREFIX not in out
        objs.append(str(ll))
    exe = tmp_path / f"t_{compiler}"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _helper_module(fn, value, pub=""):
    return (f"{pub}fn helper() -> i32\n    {value}\n\n"
            f"pub fn {fn}() -> i32\n    helper()\n")


MAIN_AB = "import ma\nimport mb\n\nfn main() -> i32\n    fa() * 10 + fb()\n"

# (id, ma's helper visibility, mb's, ma's body, mb's body)
IMPORT_VS_IMPORT = [
    ("private_private", "", "", 1, 2),
    ("pub_private", "pub ", "", 1, 2),
    ("private_pub", "", "pub ", 1, 2),
    ("pub_pub", "pub ", "pub ", 1, 2),
    # Bodies are not compared: an import is seen through its interface.
    ("identical", "", "", 1, 1),
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("pa,pb,va,vb", [c[1:] for c in IMPORT_VS_IMPORT],
                         ids=[c[0] for c in IMPORT_VS_IMPORT])
def test_import_vs_import_rejected(compiler, tmp_path, pa, pb, va, vb):
    _write(tmp_path, {"ma": _helper_module("fa", va, pa),
                      "mb": _helper_module("fb", vb, pb), "t": MAIN_AB})
    _assert_rejected(compiler, tmp_path, _conflict(tmp_path, "helper", "ma", "mb"))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_main_vs_import_rejected(compiler, tmp_path):
    """The main file is registered after its imports, so it is named second."""
    _write(tmp_path, {
        "ma": _helper_module("fa", 1),
        "t": "import ma\n\nfn helper() -> i32\n    7\n\n"
             "fn main() -> i32\n    fa() * 10 + helper()\n"})
    _assert_rejected(compiler, tmp_path, _conflict(tmp_path, "helper", "ma", "t"))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_main_shadowing_ritzlib_rejected(compiler, tmp_path):
    """rzsh's tests used to define their own `println` beside ritzlib.io's."""
    _write(tmp_path, {
        "t": "import ritzlib.io\n\nfn println(s: *u8) -> i32\n    0\n\n"
             "fn main() -> i32\n    println(c\"x\")\n"})
    io = RITZ_ROOT / "ritzlib" / "io.ritz"
    _assert_rejected(compiler, tmp_path,
                     f"{PREFIX}'println': defined in both {io} and {tmp_path / 't.ritz'}")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_nested_import_names_defining_file(compiler, tmp_path):
    """mc's helper reaches t through mb; the diagnostic names mc, not mb."""
    _write(tmp_path, {
        "ma": _helper_module("fa", 1),
        "mc": "fn helper() -> i32\n    3\n\npub fn fc() -> i32\n    helper()\n",
        "mb": "import mc\n\npub fn fb() -> i32\n    fc()\n",
        "t": MAIN_AB})
    _assert_rejected(compiler, tmp_path, _conflict(tmp_path, "helper", "ma", "mc"))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_same_file_twice_rejected(compiler, tmp_path):
    _write(tmp_path, {"t": "fn helper() -> i32\n    1\n\nfn helper() -> i32\n    2\n\n"
                           "fn main() -> i32\n    helper()\n"})
    _assert_rejected(compiler, tmp_path, _conflict(tmp_path, "helper", "t", "t"))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_same_file_twice_in_import_rejected(compiler, tmp_path):
    _write(tmp_path, {
        "ma": "fn helper() -> i32\n    1\n\nfn helper() -> i32\n    2\n\n"
              "pub fn fa() -> i32\n    helper()\n",
        "t": "import ma\n\nfn main() -> i32\n    fa()\n"})
    _assert_rejected(compiler, tmp_path, _conflict(tmp_path, "helper", "ma", "ma"))


ENUM = "import ritzlib.option\n\npub enum Color: u8\n    Red = 1\n    Blue = 2\n\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_user_fn_named_like_generated_from_rejected(compiler, tmp_path):
    """LANGUAGE_SPEC §10.4: a module may not declare `E__from` beside E."""
    _write(tmp_path, {
        "ma": ENUM + "pub fn fa() -> i32\n    1\n",
        "t": "import ma\nimport ritzlib.option\n\n"
             "fn Color__from(v: u8) -> i32\n    0\n\nfn main() -> i32\n    fa()\n"})
    _assert_rejected(compiler, tmp_path, _conflict(tmp_path, "Color__from", "ma", "t"))


# ---------------------------------------------------------------------------
# Still accepted, and still running with the right result.
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_diamond_import_runs(compiler, tmp_path):
    """mc is imported by both ma and mb: registered once, no conflict."""
    _write(tmp_path, {
        "mc": "pub fn shared() -> i32\n    4\n",
        "ma": "import mc\n\npub fn fa() -> i32\n    shared() + 1\n",
        "mb": "import mc\n\npub fn fb() -> i32\n    shared() + 2\n",
        "t": MAIN_AB})
    assert _run(compiler, tmp_path, ["t", "ma", "mb", "mc"]) == 56


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_extern_fn_in_two_modules_runs(compiler, tmp_path):
    """Duplicate `extern fn` declarations are not definitions."""
    ext = "extern fn ext_seven() -> i32\n\n"
    _write(tmp_path, {
        "me": "pub fn ext_seven() -> i32\n    7\n",
        "ma": ext + "pub fn fa() -> i32\n    ext_seven()\n",
        "mb": ext + "pub fn fb() -> i32\n    ext_seven() + 1\n",
        "t": MAIN_AB})
    assert _run(compiler, tmp_path, ["t", "ma", "mb", "me"]) == 78


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_gated_vs_ungated_not_compared(compiler, tmp_path):
    """As for consts, a [[target_os]] fn is never compared with an ungated one."""
    _write(tmp_path, {
        "ma": '[[target_os = "linux"]]\nfn helper() -> i32\n    1\n\n'
              "pub fn fa() -> i32\n    helper()\n",
        "mb": _helper_module("fb", 2),
        "t": MAIN_AB})
    proc, _ = _compile(compiler, tmp_path, "t")
    assert PREFIX not in proc.stderr + proc.stdout


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_identical_enum_from_in_two_modules_runs(compiler, tmp_path):
    """Both modules generate `Color__from`; identical enums, so no conflict.

    ritz0 emits each generated `Color__from` as a strong symbol, so its two
    objects do not link (ritz1's are weak_odr): #2160.  For ritz0 only the
    resolver's verdict is pinned.
    """
    _write(tmp_path, {
        "ma": ENUM + "pub fn fa() -> i32\n    Color.Red as i32\n",
        "mb": ENUM + "pub fn fb() -> i32\n    Color.Blue as i32\n",
        "t": MAIN_AB})
    if compiler == "ritz0":
        proc, _ = _compile(compiler, tmp_path, "t")
        assert proc.returncode == 0, proc.stderr + proc.stdout
        return
    assert _run(compiler, tmp_path, ["t", "ma", "mb"]) == 12


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_import_cycle_back_to_main_runs(compiler, tmp_path):
    """ma imports t back: t is merged once, so its fns do not meet themselves.

    ritz1 used to re-merge the main file through such a cycle (ritz1's own
    let_check.ritz <-> emitter_stmt.ritz is one).
    """
    _write(tmp_path, {
        "ma": "import t\n\npub fn fa() -> i32\n    4\n",
        "t": "import ma\n\nfn helper() -> i32\n    2\n\n"
             "fn main() -> i32\n    fa() * 10 + helper()\n"})
    assert _run(compiler, tmp_path, ["t", "ma"]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_one_module_by_two_spellings_runs(compiler, tmp_path):
    """mc reached as lib.mc and through the symlink alias.mc is one module."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "alias").symlink_to(tmp_path / "lib")
    _write(tmp_path, {
        "lib/mc": "pub fn shared() -> i32\n    4\n",
        "ma": "import lib.mc\n\npub fn fa() -> i32\n    shared() + 1\n",
        "mb": "import alias.mc\n\npub fn fb() -> i32\n    shared() + 2\n",
        "t": MAIN_AB})
    assert _run(compiler, tmp_path, ["t", "ma", "mb", "lib/mc"]) == 56
