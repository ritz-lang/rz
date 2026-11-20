"""A private fn is visible only in its own module (AGAST #1858, LARB review/4
infra.md M7; LANGUAGE_SPEC §15.2, §15.3).

Two modules may each define a private `fn be16` without a clash: neither is
visible outside its own file, so neither lands in the importer's namespace.
Before this, both compilers rejected the pair with "Conflicting function
definition" (#2148), and packages renamed their helpers with a prefix to dodge
it (eight copies of byte-order helpers across the infra packages).

Still rejected, by test_import_fn_conflict.py: two `pub` fns of one name, and a
fn beside a `pub` one its file can see (the importer's own `println` beside
ritzlib.io's). Calling another module's private fn is still the located
§15.2 error, even when two imports each have one of that name.

Every case runs ritz0 and both ritz1 binaries, compiles each file to its own
object as build.py does, links and runs.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

CONFLICT = "Conflicting function definition"


def _write(tmp_path, files):
    for name, text in files.items():
        (tmp_path / f"{name}.ritz").write_text(text)


def _compile(compiler, tmp_path, name):
    src = tmp_path / f"{name}.ritz"
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    args = [str(src), "-o", str(ll)]
    if compiler == "ritz0":
        proc = run_ritz0(args + ["--no-runtime"], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary)] + args, cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    return proc, ll


def _run(compiler, tmp_path, names):
    """Compile each file to its own object, link, run; return the exit code."""
    objs = [str(RITZ_START)]
    for name in names:
        proc, ll = _compile(compiler, tmp_path, name)
        out = proc.stderr + proc.stdout
        assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected {name}:\n{out}"
        assert CONFLICT not in out, out
        objs.append(str(ll))
    exe = tmp_path / f"t_{compiler}"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _be16_module(fn, hi, lo):
    """A module whose `pub fn {fn}` reads through its own private `be16`.

    The two modules' `be16`s differ, so a call bound to the wrong one shows
    in the exit code."""
    return (f"fn be16(p: *u8) -> i32\n"
            f"    ((*p as i32) << 8) | (*(p + 1) as i32)\n\n"
            f"pub fn {fn}() -> i32\n"
            f"    var b: [2]u8 = [{hi}, {lo}]\n"
            f"    be16(@b[0])\n")


MA = _be16_module("fa", 0, 3)          # be16 -> 3
MB = ("fn be16(p: *u8) -> i32\n"       # a little-endian `be16` -> 4
      "    ((*(p + 1) as i32) << 8) | (*p as i32)\n\n"
      "pub fn fb() -> i32\n"
      "    var b: [2]u8 = [4, 0]\n"
      "    be16(@b[0])\n")
MAIN_AB = "import ma\nimport mb\n\nfn main() -> i32\n    fa() * 10 + fb()\n"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_two_imports_each_with_a_private_be16(compiler, tmp_path):
    """The acceptance case: each module's calls reach its own be16."""
    _write(tmp_path, {"ma": MA, "mb": MB, "t": MAIN_AB})
    assert _run(compiler, tmp_path, ["ma", "mb", "t"]) == 34


@pytest.mark.parametrize("compiler", COMPILERS)
def test_importer_private_beside_an_imports_private(compiler, tmp_path):
    """The compiled file's own private be16 is the one its body calls."""
    _write(tmp_path, {
        "ma": MA,
        "t": "import ma\n\nfn be16(p: *u8) -> i32\n    5\n\n"
             "fn main() -> i32\n    var b: [2]u8 = [0, 0]\n"
             "    fa() * 10 + be16(@b[0])\n"})
    assert _run(compiler, tmp_path, ["ma", "t"]) == 35


@pytest.mark.parametrize("compiler", COMPILERS)
def test_nested_private_beside_its_importers_private(compiler, tmp_path):
    """mb imports mc; both have a private be16, and so does ma."""
    _write(tmp_path, {
        "ma": MA,
        "mc": _be16_module("fc", 0, 1),
        "mb": "import mc\n\nfn be16(p: *u8) -> i32\n    2\n\n"
              "pub fn fb() -> i32\n    var b: [2]u8 = [9, 9]\n"
              "    fc() * 10 + be16(@b[0])\n",
        "t": MAIN_AB})
    # fa = 3, fb = fc * 10 + 2 = 12
    assert _run(compiler, tmp_path, ["ma", "mc", "mb", "t"]) == 42


@pytest.mark.parametrize("compiler", COMPILERS)
def test_private_beside_an_unseen_pub(compiler, tmp_path):
    """ma's private be16 and mb's `pub` one: t sees only mb's, ma only its own."""
    _write(tmp_path, {
        "ma": MA,
        "mb": MB.replace("fn be16", "pub fn be16"),
        "t": "import ma\nimport mb\n\nfn main() -> i32\n"
             "    var b: [2]u8 = [6, 0]\n    fa() * 10 + be16(@b[0])\n"})
    assert _run(compiler, tmp_path, ["ma", "mb", "t"]) == 36


@pytest.mark.parametrize("compiler", COMPILERS)
def test_calling_one_of_two_private_be16s_is_a_located_error(compiler, tmp_path):
    """§15.2's error is still at the call when two imports each have one."""
    _write(tmp_path, {
        "ma": MA, "mb": MB,
        "t": "import ma\nimport mb\n\nfn main() -> i32\n"
             "    var b: [2]u8 = [0, 0]\n    be16(@b[0])\n"})
    proc, _ = _compile(compiler, tmp_path, "t")
    out = proc.stderr + proc.stdout
    assert proc.returncode != 0, f"{compiler} accepted a private call:\n{out}"
    assert "`be16` is private to m" in out, out
    assert f"{tmp_path / 't.ritz'}:6:" in out or "t.ritz:6:" in out, out
    assert CONFLICT not in out, out
