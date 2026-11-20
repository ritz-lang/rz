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

Rejected: two `pub` fns of one name in two imports, a fn beside a `pub` one
its file imports (the rzsh tests' shadowed `println`), nested imports (the
diagnostic names the file that defined the fn), two in one file, and a user fn
named like a generated `E__from`.

Since AGAST #1858 a private fn is in its own file's namespace only, so two
files' private fns of one name, or a private one beside a `pub` one its file
doesn't import, coexist and each file runs its own (more in
test_private_fn_no_clash.py).

Two `[[target_os]]` variants gated to the same target are rejected too
(LANGUAGE_SPEC §17.2, AGAST #4055): both compilers used to keep the first
and run it.  Rejected whatever the target being compiled, as for structs and
consts: in one file, across two imports, and gated to another target.

A `[[target_os]]` fn beside an ungated one of the same name conflicts on the
gated target (AGAST #4270), as for structs (#4054/#4111): after target_os
filtering at most one definition of a name may survive.  Onto another target
the gated one is filtered out, so nothing conflicts.

Accepted, and still running correctly: a diamond import (one module reached
twice is registered once), the same name as `extern fn` in two modules, and
identical `enum E: u8` in two modules that import ritzlib.option (each
generates `E__from`; the enums are already checked identical).
"""

import os
import re
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


def _compile(compiler, tmp_path, name, target_os=None):
    src = tmp_path / f"{name}.ritz"
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    args = [str(src), "-o", str(ll)]
    if target_os is not None:
        args += ["--target-os", target_os]
    if compiler == "ritz0":
        proc = run_ritz0(args + ["--no-runtime"], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary)] + args, cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    return proc, ll


def _conflict(tmp_path, name, first, second):
    return (f"{PREFIX}'{name}': defined in both "
            f"{tmp_path / (first + '.ritz')} and {tmp_path / (second + '.ritz')}")


def _assert_rejected(compiler, tmp_path, diag, main="t", target_os=None):
    proc, _ = _compile(compiler, tmp_path, main, target_os)
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
    ("pub_pub", "pub ", "pub ", 1, 2),
    # Bodies are not compared: an import is seen through its interface.
    ("identical", "pub ", "pub ", 1, 1),
]

# Neither module imports the other, so a private helper is in no namespace
# but its own (AGAST #1858): each module's fa/fb runs its own helper.
IMPORT_BESIDE_IMPORT = [
    ("private_private", "", "", 1, 2),
    ("pub_private", "pub ", "", 1, 2),
    ("private_pub", "", "pub ", 1, 2),
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
@pytest.mark.parametrize("pa,pb,va,vb", [c[1:] for c in IMPORT_BESIDE_IMPORT],
                         ids=[c[0] for c in IMPORT_BESIDE_IMPORT])
def test_private_beside_import_runs(compiler, tmp_path, pa, pb, va, vb):
    _write(tmp_path, {"ma": _helper_module("fa", va, pa),
                      "mb": _helper_module("fb", vb, pb), "t": MAIN_AB})
    assert _run(compiler, tmp_path, ["t", "ma", "mb"]) == va * 10 + vb


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_main_vs_import_rejected(compiler, tmp_path):
    """The main file is registered after its imports, so it is named second.
    ma's helper is `pub`, so it is in t's namespace beside t's own."""
    _write(tmp_path, {
        "ma": _helper_module("fa", 1, "pub "),
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
        "ma": _helper_module("fa", 1, "pub "),
        "mc": "pub fn helper() -> i32\n    3\n\npub fn fc() -> i32\n    helper()\n",
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


def _gated(os_name, fn, value):
    return f'[[target_os = "{os_name}"]]\npub fn {fn}() -> i32\n    {value}\n\n'


# (id, target gated twice, target compiled for).  AGAST #4055's repro is
# linux/linux; harland/linux checks the variants that never reach the module.
SAME_TARGET = [("compiled_target", "linux", "linux"),
               ("other_target", "harland", "linux")]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("gate,target_os", [c[1:] for c in SAME_TARGET],
                         ids=[c[0] for c in SAME_TARGET])
def test_same_target_twice_in_one_file_rejected(compiler, tmp_path, gate, target_os):
    _write(tmp_path, {"t": _gated(gate, "get_platform_id", 1)
                      + _gated(gate, "get_platform_id", 2)
                      + "fn main() -> i32\n    0\n"})
    _assert_rejected(compiler, tmp_path,
                     _conflict(tmp_path, "get_platform_id", "t", "t"),
                     target_os=target_os)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("gate,target_os", [c[1:] for c in SAME_TARGET],
                         ids=[c[0] for c in SAME_TARGET])
def test_same_target_across_imports_rejected(compiler, tmp_path, gate, target_os):
    """Identical bodies too: as for ungated fns, bodies are not compared."""
    _write(tmp_path, {"ma": _gated(gate, "helper", 1) + "pub fn fa() -> i32\n    1\n",
                      "mb": _gated(gate, "helper", 1) + "pub fn fb() -> i32\n    2\n",
                      "t": MAIN_AB})
    _assert_rejected(compiler, tmp_path, _conflict(tmp_path, "helper", "ma", "mb"),
                     target_os=target_os)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_main_vs_import_same_target_rejected(compiler, tmp_path):
    """Named in registration order, as for ungated fns: the import first."""
    _write(tmp_path, {
        "ma": _gated("linux", "helper", 1) + "pub fn fa() -> i32\n    helper()\n",
        "t": "import ma\n\n" + _gated("linux", "helper", 7)
             + "fn main() -> i32\n    fa() * 10 + helper()\n"})
    _assert_rejected(compiler, tmp_path, _conflict(tmp_path, "helper", "ma", "t"))


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
# ritz1 checks each import against those already merged, so the pair must
# conflict whichever definition is seen first.
@pytest.mark.parametrize("first,second", [("ma", "mb"), ("mb", "ma")],
                         ids=["gated_first", "ungated_first"])
def test_gated_vs_ungated_rejected(compiler, tmp_path, first, second):
    """A [[target_os]] fn beside an ungated one conflicts on its own target
    (AGAST #4270), as for structs: at most one definition survives filtering.

    Onto another target the gated one is filtered out, so there is nothing to
    compare and the ungated one is accepted.
    """
    _write(tmp_path, {
        "ma": '[[target_os = "linux"]]\nfn helper() -> i32\n    1\n\n'
              "pub fn fa() -> i32\n    helper()\n",
        "mb": _helper_module("fb", 2),
        "t": f"import {first}\nimport {second}\n\n"
             "fn main() -> i32\n    fa() * 10 + fb()\n"})
    _assert_rejected(compiler, tmp_path,
                     _conflict(tmp_path, "helper", first, second),
                     target_os="linux")
    proc, _ = _compile(compiler, tmp_path, "t", target_os="harland")
    assert PREFIX not in proc.stderr + proc.stdout, (compiler, proc.stderr)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_one_variant_per_target_runs(compiler, tmp_path):
    """A linux and a harland variant, in one file and across imports: linux's runs."""
    _write(tmp_path, {
        "ma": _gated("harland", "fa", 9) + _gated("linux", "fa", 4),
        "mb": _gated("linux", "fb", 2),
        "mc": _gated("harland", "fb", 8),
        "t": "import ma\nimport mb\nimport mc\n\nfn main() -> i32\n    fa() * 10 + fb()\n"})
    assert _run(compiler, tmp_path, ["t", "ma", "mb", "mc"]) == 42
    for name in ("t", "ma", "mb", "mc"):
        proc, _ = _compile(compiler, tmp_path, name, "harland")
        assert PREFIX not in proc.stderr + proc.stdout, (name, proc.stderr)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_identical_enum_from_in_two_modules_runs(compiler, tmp_path):
    """Both modules generate `Color__from`; identical enums, so no conflict.

    Each object defines `Color__from`, so it must be a mergeable `weak_odr`
    definition, not a strong one: ritz0's used to be strong, and the two
    objects failed to link with a duplicate symbol (#2160).
    """
    _write(tmp_path, {
        "ma": ENUM + "pub fn fa() -> i32\n    Color.Red as i32\n",
        "mb": ENUM + "pub fn fb() -> i32\n    Color.Blue as i32\n",
        "t": MAIN_AB})
    assert _run(compiler, tmp_path, ["t", "ma", "mb"]) == 12


@pytest.mark.integration
def test_ritz0_generated_from_weak_user_fn_strong(tmp_path):
    """ritz0 (#2160): only the generated fn is weak_odr; user fns stay strong.

    weak_odr, not linkonce_odr: an importer may only declare `E__from`, so
    the definition must survive even where its own module does not call it.
    """
    _write(tmp_path, {"ma": ENUM + "pub fn fa() -> i32\n    Color.Red as i32\n"})
    proc, ll = _compile("ritz0", tmp_path, "ma")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    defs = [l for l in ll.read_text().splitlines() if l.startswith("define ")]

    def define(name):
        hits = [l for l in defs if re.search(r'@"?%s"?\(' % name, l)]
        assert len(hits) == 1, (name, defs)
        return hits[0]

    assert define("Color__from").startswith("define weak_odr "), defs
    fa = define("fa")
    assert not any(w in fa for w in ("weak", "linkonce", "internal")), fa


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
