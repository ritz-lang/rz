"""LANGUAGE_SPEC §17.2: `[[target_arch = "<arch>"]]` (AGAST #4117).

Every `SYS_*` Linux number in ritzlib is x86_64's, and `syscall0..6` are
`asm x86_64`, but nothing — spec, ritz0, ritz1 — knew the target
architecture.  This pins the attribute's contract, with ritz0 as the oracle
for ritz1 exactly as `test_ritz1_target_os.py` does for `[[target_os]]`:

* an item carrying `[[target_arch = "X"]]` is kept iff X == the target arch;
* an item with no `target_arch` is always kept;
* when an item carries both `target_os` and `target_arch`, both must match;
* without a flag the arch is the first component of the target triple
  (ritz0's `--target`, default `x86_64-unknown-linux-gnu`), so `x86_64`.

`--target-arch` selects it, as `--target-os` does.  ritz0 derives its
default from `--target`; ritz1 emits an x86_64 triple and defaults to
`x86_64`.

The target_arch flag only selects conditional-compilation variants: both
compilers still emit x86_64 machine code, so a program compiled for
`aarch64` runs here and its exit code says which variant was kept.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

X86 = 3
ARM = 7

# aarch64 first, so a first-wins dedup can't pass by accident.
FN_VARIANTS = """\
[[target_arch = "aarch64"]]
fn pick() -> i32
    return 7

[[target_arch = "x86_64"]]
fn pick() -> i32
    return 3

fn main() -> i32
    return pick()
"""

# x86_64 first: a last-wins dedup can't pass by accident either.
FN_VARIANTS_X86_FIRST = """\
[[target_arch = "x86_64"]]
fn pick() -> i32
    return 3

[[target_arch = "aarch64"]]
fn pick() -> i32
    return 7

fn main() -> i32
    return pick()
"""

# Consts take attrs too (ritzlib/sys's per-target syscall numbers).
CONST_VARIANTS = """\
[[target_arch = "aarch64"]]
const K: i32 = 7

[[target_arch = "x86_64"]]
const K: i32 = 3

fn main() -> i32
    return K
"""

PROGRAMS = {
    "fn_variants": FN_VARIANTS,
    "fn_variants_x86_first": FN_VARIANTS_X86_FIRST,
    "const_variants": CONST_VARIANTS,
}

# (--target-arch passed, expected exit). None = flag absent -> x86_64.
TARGETS = [(None, X86), ("x86_64", X86), ("aarch64", ARM)]

# Both attributes on one item: the pair selects, so neither alone decides.
BOTH_GATES = """\
[[target_os = "harland", target_arch = "aarch64"]]
fn pick() -> i32
    return 7

[[target_os = "linux", target_arch = "x86_64"]]
fn pick() -> i32
    return 3

fn main() -> i32
    return pick()
"""


def _ritz1(cwd: Path, argv: list) -> subprocess.CompletedProcess:
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [str(RITZ1_BIN), *argv], cwd=cwd, env=env, capture_output=True, text=True, timeout=300
    )


def _ritz1_args(src: Path, ll: Path, cwd: Path, target_arch, target_os=None,
                flag_first: bool = False) -> list:
    """`<src> -o <ll>` then `-I` and the target flags in either order."""
    dash_i = ["-I", str(cwd)]
    tos = ["--target-os", target_os] if target_os is not None else []
    arch = ["--target-arch", target_arch] if target_arch is not None else []
    extra = tos + arch
    return [str(src), "-o", str(ll), *(extra + dash_i if flag_first else dash_i + extra)]


def _link_run(compiler: str, cwd: Path, ll: Path, exe: Path) -> int:
    link_cmd = ["clang", str(ll), str(RITZ_START), "-o", str(exe), "-nostdlib"]
    link = fast_link.clang(link_cmd, cwd=cwd, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _run_ritz0(tmp_path: Path, name: str, program: str, target_arch,
               ll_name=None, extra=()) -> int:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / (ll_name or f"{name}.r0.{target_arch}.ll")
    args = [str(src), "-o", str(ll), "--no-runtime", *extra]
    if target_arch is not None:
        args += ["--target-arch", target_arch]
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = run_ritz0(args, cwd=tmp_path, env=env, timeout=300)
    assert comp.returncode == 0, f"ritz0 failed on {name}:\n{comp.stderr[-2000:]}"
    return _link_run("ritz0", tmp_path, ll, tmp_path / f"{name}.r0")


def _run_ritz1(tmp_path: Path, name: str, program: str, target_arch,
               target_os=None, flag_first=False, ll_name=None) -> int:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / (ll_name or f"{name}.r1.{target_arch}.{target_os}.ll")
    comp = _ritz1(tmp_path, _ritz1_args(src, ll, tmp_path, target_arch, target_os,
                                        flag_first))
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed on {name} (--target-arch {target_arch}):\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return _link_run("ritz1", tmp_path, ll, tmp_path / f"{name}.r1")


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
@pytest.mark.parametrize("target_arch,expected", TARGETS)
def test_ritz0_oracle(ritz_start, tmp_path, name, target_arch, expected):
    """Pins the expectation to ritz0's behaviour, so ritz1 is measured against it."""
    assert _run_ritz0(tmp_path, name, PROGRAMS[name], target_arch) == expected


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
@pytest.mark.parametrize("target_arch,expected", TARGETS)
def test_ritz1_selects_variant_for_target_arch(ritz1_bin, tmp_path, name,
                                               target_arch, expected):
    assert _run_ritz1(tmp_path, name, PROGRAMS[name], target_arch) == expected


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("target_os,target_arch,expected", [
    ("linux", "x86_64", X86),
    ("harland", "aarch64", ARM),
])
def test_target_os_and_arch_must_both_match(ritz1_bin, tmp_path, compiler,
                                            target_os, target_arch, expected):
    if compiler == "ritz0":
        got = _run_ritz0(tmp_path, "both", BOTH_GATES, target_arch,
                         extra=["--target-os", target_os])
    else:
        got = _run_ritz1(tmp_path, "both", BOTH_GATES, target_arch,
                         target_os=target_os)
    assert got == expected


@pytest.mark.integration
def test_ritz1_target_arch_flag_position(ritz1_bin, tmp_path):
    """`--target-arch` is accepted before or after `-I`."""
    assert _run_ritz1(tmp_path, "pos", FN_VARIANTS, "aarch64",
                      flag_first=True) == ARM
    assert _run_ritz1(tmp_path, "pos", FN_VARIANTS, "aarch64",
                      flag_first=False) == ARM


@pytest.mark.integration
def test_ritz1_target_arch_without_value_is_an_error(ritz1_bin, tmp_path):
    src = tmp_path / "noval.ritz"
    src.write_text(FN_VARIANTS)
    ll = tmp_path / "noval.ll"
    comp = _ritz1(tmp_path, [str(src), "-o", str(ll), "--target-arch"])
    assert comp.returncode != 0
    assert not ll.exists(), "wrote output despite a malformed command line"
    assert "--target-arch" in comp.stderr


@pytest.mark.integration
def test_ritz0_default_arch_comes_from_the_target_triple(ritz_start, tmp_path):
    """No --target-arch: the first component of --target decides."""
    assert _run_ritz0(tmp_path, "triple", FN_VARIANTS, None,
                      extra=["--target", "aarch64-unknown-linux-gnu"]) == ARM
    # An explicit --target-arch overrides the triple's arch.
    assert _run_ritz0(tmp_path, "triple", FN_VARIANTS, "x86_64",
                      extra=["--target", "aarch64-unknown-linux-gnu"]) == X86


@pytest.mark.integration
def test_ritz1_cache_does_not_splice_other_arch_ir(ritz1_bin, tmp_path):
    """The sig cache is keyed on the target arch, like the target OS."""
    assert _run_ritz1(tmp_path, "cache", FN_VARIANTS, "x86_64",
                      ll_name="out.ll") == X86
    assert _run_ritz1(tmp_path, "cache", FN_VARIANTS, "aarch64",
                      ll_name="out.ll") == ARM


@pytest.mark.integration
def test_ritz0_recompiles_when_only_the_arch_changes(ritz_start, tmp_path):
    """The compile-mode key includes the arch, so the .ll is not reused."""
    assert _run_ritz0(tmp_path, "r0cache", FN_VARIANTS, "x86_64",
                      ll_name="out.ll") == X86
    assert _run_ritz0(tmp_path, "r0cache", FN_VARIANTS, "aarch64",
                      ll_name="out.ll") == ARM
