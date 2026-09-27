"""Regression tests for AGAST #1550: ritz1 `--target-os` and `[[target_os]]`.

ritz1's `check_target_os_filter` hard-coded "linux", and its CLI had no
`--target-os`, so the 19 freestanding `[[bin]]`s with `target_os = "harland"`
could not be built with ritz1 (build.py refused, #1473).

The contract, matching ritz0 (`ritz0.py --target-os`, default "linux"):

* `--target-os <os>` may appear anywhere after `-o <out>`, before or after `-I`.
* An item carrying `[[target_os = "X"]]` is kept iff X == the target OS.
  Items with no target_os attribute are always kept.
* Without the flag the target is "linux".

ritz0 is the oracle: every program is compiled by both and must agree on the
exit code, which says which variant of `pick()` / `K` was kept.

ritz1 also caches IR next to the source (`<src>.ritz.sig`). That cache must
be keyed on the target OS too, or a harland compile of a file reuses the IR a
linux compile of the same file left behind. The cache tests pin that.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

LINUX_EXIT = 3
HARLAND_EXIT = 7

# The ticket's test: one fn, two target variants; harland listed first so a
# first-wins dedup can't pass by accident.
FN_VARIANTS = """\
[[target_os = "harland"]]
fn pick() -> i32
    return 7

[[target_os = "linux"]]
fn pick() -> i32
    return 3

fn main() -> i32
    return pick()
"""

# Same, linux first: a last-wins dedup can't pass by accident either.
FN_VARIANTS_LINUX_FIRST = """\
[[target_os = "linux"]]
fn pick() -> i32
    return 3

[[target_os = "harland"]]
fn pick() -> i32
    return 7

fn main() -> i32
    return pick()
"""

# Consts take attrs too (ritzlib/sys uses per-OS syscall numbers).
CONST_VARIANTS = """\
[[target_os = "harland"]]
const K: i32 = 7

[[target_os = "linux"]]
const K: i32 = 3

fn main() -> i32
    return K
"""

PROGRAMS = {
    "fn_variants": FN_VARIANTS,
    "fn_variants_linux_first": FN_VARIANTS_LINUX_FIRST,
    "const_variants": CONST_VARIANTS,
}


def _make(target_dir: str, target: str, product: Path) -> None:
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", target_dir, target],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not product.exists():
        pytest.fail(
            f"could not build {product}:\n{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


@pytest.fixture(scope="module")
def ritz_start() -> Path:
    _make("runtime", RITZ_START.name, RITZ_START)
    return RITZ_START


@pytest.fixture(scope="module")
def ritz1_bin(ritz_start) -> Path:
    # A stale binary would test the old filter.
    _make("ritz1", "ritz1", RITZ1_BIN)
    return RITZ1_BIN


def _ritz1(cwd: Path, argv: list) -> subprocess.CompletedProcess:
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [str(RITZ1_BIN), *argv], cwd=cwd, env=env, capture_output=True, text=True, timeout=300
    )


def _ritz1_args(src: Path, ll: Path, cwd: Path, target_os, flag_first: bool) -> list:
    """`<src> -o <ll>` then `-I` and `--target-os` in either order."""
    dash_i = ["-I", str(cwd)]
    tos = ["--target-os", target_os] if target_os is not None else []
    return [str(src), "-o", str(ll), *(tos + dash_i if flag_first else dash_i + tos)]


def _link_run(compiler: str, cwd: Path, ll: Path, exe: Path) -> int:
    # Both link the Linux _start: ritz0 runs with --no-runtime, since its
    # embedded harland runtime (--target-os harland) cannot run on this host.
    link_cmd = ["clang", str(ll), str(RITZ_START), "-o", str(exe), "-nostdlib"]
    link = subprocess.run(link_cmd, cwd=cwd, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _run_ritz0(tmp_path: Path, name: str, program: str, target_os) -> int:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}.r0.ll"
    cmd = ["python3", str(RITZ0), str(src), "-o", str(ll), "--no-runtime"]
    if target_os is not None:
        cmd += ["--target-os", target_os]
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = subprocess.run(cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)
    assert comp.returncode == 0, f"ritz0 failed on {name}:\n{comp.stderr[-2000:]}"
    return _link_run("ritz0", tmp_path, ll, tmp_path / f"{name}.r0")


def _run_ritz1(tmp_path: Path, name: str, program: str, target_os, flag_first=False,
               ll_name=None) -> int:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / (ll_name or f"{name}.r1.{target_os}.ll")
    comp = _ritz1(tmp_path, _ritz1_args(src, ll, tmp_path, target_os, flag_first))
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed on {name} (--target-os {target_os}):\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return _link_run("ritz1", tmp_path, ll, tmp_path / f"{name}.r1")


# (target_os passed, expected exit). None = flag absent → ritz0's default.
TARGETS = [(None, LINUX_EXIT), ("linux", LINUX_EXIT), ("harland", HARLAND_EXIT)]


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
@pytest.mark.parametrize("target_os,expected", TARGETS)
def test_ritz0_oracle(ritz_start, tmp_path, name, target_os, expected):
    """Pins the expectation to ritz0's behaviour, so ritz1 is measured against it."""
    assert _run_ritz0(tmp_path, name, PROGRAMS[name], target_os) == expected


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
@pytest.mark.parametrize("target_os,expected", TARGETS)
def test_ritz1_selects_variant_for_target_os(ritz1_bin, tmp_path, name, target_os, expected):
    """Before #1550: harland picked linux (3), because 'linux' was hard-coded."""
    assert _run_ritz1(tmp_path, name, PROGRAMS[name], target_os) == expected


@pytest.mark.integration
@pytest.mark.parametrize("flag_first", [True, False], ids=["before_-I", "after_-I"])
def test_ritz1_target_os_flag_position(ritz1_bin, tmp_path, flag_first):
    """`--target-os` is accepted before or after `-I`."""
    assert _run_ritz1(tmp_path, "pos", FN_VARIANTS, "harland", flag_first) == HARLAND_EXIT


@pytest.mark.integration
def test_ritz1_target_os_without_value_is_an_error(ritz1_bin, tmp_path):
    src = tmp_path / "noval.ritz"
    src.write_text(FN_VARIANTS)
    ll = tmp_path / "noval.ll"
    comp = _ritz1(tmp_path, [str(src), "-o", str(ll), "--target-os"])
    assert comp.returncode != 0
    assert not ll.exists(), "wrote output despite a malformed command line"
    assert "--target-os" in comp.stderr


@pytest.mark.integration
def test_ritz1_unmatched_os_keeps_unattributed_items(ritz1_bin, tmp_path):
    """An OS with no variant drops every attributed item but keeps the rest."""
    program = (
        '[[target_os = "harland"]]\nconst K: i32 = 7\n\n'
        "const J: i32 = 5\n\nfn main() -> i32\n    return J\n"
    )
    assert _run_ritz1(tmp_path, "unmatched", program, "prism") == 5


# --- the .ritz.sig cache must be keyed on the target OS -------------------


@pytest.mark.integration
@pytest.mark.parametrize("first,second,expected", [
    ("linux", "harland", HARLAND_EXIT),
    ("harland", "linux", LINUX_EXIT),
    (None, "harland", HARLAND_EXIT),
])
def test_ritz1_cache_does_not_splice_other_targets_ir(ritz1_bin, tmp_path, first, second,
                                                      expected):
    """Path (b): a fresh output path, same source, different target OS."""
    _run_ritz1(tmp_path, "cache", FN_VARIANTS, first, ll_name="first.ll")
    assert _run_ritz1(tmp_path, "cache", FN_VARIANTS, second, ll_name="second.ll") == expected


@pytest.mark.integration
def test_ritz1_cache_does_not_keep_other_targets_ll(ritz1_bin, tmp_path):
    """Path (a): same output path, already newer than the source."""
    _run_ritz1(tmp_path, "samell", FN_VARIANTS, "linux", ll_name="out.ll")
    assert _run_ritz1(tmp_path, "samell", FN_VARIANTS, "harland", ll_name="out.ll") == HARLAND_EXIT


@pytest.mark.integration
def test_ritz1_cache_still_reuses_for_same_target(ritz1_bin, tmp_path):
    """Keying on the target must not switch the cache off."""
    src = tmp_path / "reuse.ritz"
    src.write_text(FN_VARIANTS)
    ll = tmp_path / "reuse.ll"
    args = _ritz1_args(src, ll, tmp_path, "harland", flag_first=False)
    assert _ritz1(tmp_path, args).returncode == 0
    again = _ritz1(tmp_path, args)
    assert again.returncode == 0
    assert "Skipped (unchanged)" in again.stdout
