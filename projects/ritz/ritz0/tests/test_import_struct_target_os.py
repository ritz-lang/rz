"""Same-named `[[target_os]]` struct variants (AGAST #4054).

LANGUAGE_SPEC §17.2: `[[target_os = "<os>"]]` applies to `fn`, `struct` and
`const`; the item exists only when compiling for `<os>`.  ritz0's import
resolver kept gated fns and consts as per-target variants but allowed a
struct name only once (or an identical duplicate), so a linux and a harland
`struct PlatformInfo` failed with "Conflicting struct definition", while
ritz1 and ritz1_selfhosted compiled them.

Accepted on all three compilers: twin variants in one file and across two
imports, each target picking its own layout (`--target-os harland` compiles a
harland-layout literal that the linux layout would reject).

Rejected on all three compilers (AGAST #4111): two ungated or two
same-target structs that differ, and a gated struct beside a differing
ungated one, but only on the target where both exist.
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

PREFIX = "Conflicting struct definition for 'P'"

LINUX_P = '[[target_os = "linux"]]\npub struct P\n    a: i32\n\n'
HARLAND_P = '[[target_os = "harland"]]\npub struct P\n    h: i64\n    g: i64\n\n'
UNGATED_P = "pub struct P\n    u: i64\n\n"

# Each target's main builds its own layout: on the wrong layout it fails to
# compile, so a successful compile proves which variant was selected.
MAINS = ('[[target_os = "linux"]]\nfn main() -> i32\n'
         "    var p: P = P { a: 42 }\n    p.a\n\n"
         '[[target_os = "harland"]]\nfn main() -> i32\n'
         "    var p: P = P { h: 5, g: 6 }\n    (p.h + p.g) as i32\n")


def _write(tmp_path, files):
    for name, text in files.items():
        (tmp_path / f"{name}.ritz").write_text(text)


def _compile(compiler, tmp_path, name, target_os="linux"):
    src = tmp_path / f"{name}.ritz"
    ll = tmp_path / f"{name}_{compiler}_{target_os}.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    args = [str(src), "-o", str(ll), "--target-os", target_os]
    if compiler == "ritz0":
        proc = run_ritz0(args + ["--no-runtime"], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary)] + args, cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    return proc, ll


def _accepted(compiler, tmp_path, name, target_os="linux"):
    proc, ll = _compile(compiler, tmp_path, name, target_os)
    out = proc.stderr + proc.stdout
    assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected {name}:\n{out}"
    assert PREFIX not in out
    return ll


def _run(compiler, tmp_path, names):
    """Compile each file (linux) to its own object, link, run; return the exit code."""
    objs = [str(RITZ_START)] + [str(_accepted(compiler, tmp_path, n)) for n in names]
    exe = tmp_path / f"t_{compiler}"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_twin_in_one_file_runs_linux_layout(compiler, tmp_path):
    _write(tmp_path, {"t": LINUX_P + HARLAND_P + MAINS})
    assert _run(compiler, tmp_path, ["t"]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_twin_in_one_file_harland_layout(compiler, tmp_path):
    """`--target-os harland` selects the harland layout (compile only)."""
    _write(tmp_path, {"t": HARLAND_P + LINUX_P + MAINS})
    _accepted(compiler, tmp_path, "t", "harland")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_twin_across_imports(compiler, tmp_path):
    """ma holds the linux variant, mb the harland one; both targets compile."""
    _write(tmp_path, {"ma": LINUX_P, "mb": HARLAND_P,
                      "t": "import ma\nimport mb\n\n" + MAINS})
    _accepted(compiler, tmp_path, "t", "harland")
    assert _run(compiler, tmp_path, ["t", "ma", "mb"]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_identical_same_target_in_two_imports_accepted(compiler, tmp_path):
    """As for ungated structs, an identical repeat is not a conflict."""
    _write(tmp_path, {"ma": LINUX_P, "mb": LINUX_P,
                      "t": "import ma\nimport mb\n\n" + MAINS})
    _accepted(compiler, tmp_path, "t")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_identical_repeat_in_one_file_accepted(compiler, tmp_path):
    """Another line, a comment between, `pub` dropped: still the same P."""
    _write(tmp_path, {"t": UNGATED_P + "# again\nstruct P\n    u: i64\n\n"
                      "fn main() -> i32\n    var p: P = P { u: 3 }\n    p.u as i32\n"})
    _accepted(compiler, tmp_path, "t")


# (id, source, target_os) — each must fail with the struct conflict.
REJECTED = [
    ("ungated_differing", UNGATED_P + "pub struct P\n    v: i32\n\n", "linux"),
    ("same_target_differing", LINUX_P + '[[target_os = "linux"]]\n'
     "pub struct P\n    b: i64\n\n", "linux"),
    # Rejected even when compiling for another target, as for fns and consts.
    ("other_target_differing", HARLAND_P + '[[target_os = "harland"]]\n'
     "pub struct P\n    b: i64\n\n", "linux"),
    ("gated_beside_ungated", LINUX_P + UNGATED_P, "linux"),
    # ritz1 keeps one file's items in one list: the conflict must also be
    # seen when the two definitions come from two imports.
    ("ungated_across_imports", "import ma\nimport mb\n\n", "linux"),
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("src,target_os", [c[1:] for c in REJECTED],
                         ids=[c[0] for c in REJECTED])
def test_conflict_rejected(compiler, tmp_path, src, target_os):
    _write(tmp_path, {"ma": UNGATED_P, "mb": "pub struct P\n    v: i32\n\n",
                      "t": src + "fn main() -> i32\n    0\n"})
    proc, _ = _compile(compiler, tmp_path, "t", target_os)
    out = proc.stderr + proc.stdout
    assert proc.returncode != 0, f"{compiler} accepted a conflicting struct:\n{out}"
    assert PREFIX in out, out


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_gated_beside_ungated_other_target_accepted(compiler, tmp_path):
    """On harland the linux variant does not exist, so the ungated P stands."""
    _write(tmp_path, {"t": LINUX_P + UNGATED_P +
                      "fn main() -> i32\n    var p: P = P { u: 3 }\n    p.u as i32\n"})
    _accepted(compiler, tmp_path, "t", "harland")
