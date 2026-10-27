"""ritz1 reads RITZ_PATH from its environment via ritzlib.os.env (AGAST #1750).

ritz1's parse_cli used to call ritzlib/env.ritz's `getenv(envp, "RITZ_PATH")`
on the envp handed to a 3-arg main. #1750 deleted env.ritz: ritz1 now has a
2-arg main, links runtime/ritz_start.o, and reads RITZ_PATH with
`env_get_or` from ritzlib/os/env.ritz (/proc/self/environ).

These tests pin the lookup itself. A module that lives outside the source
directory is only reachable through RITZ_PATH or `-I`, so whether ritz1
compiles the program tells us which search paths it actually saw:

  * RITZ_PATH alone (multi-entry, colon-separated) is honoured;
  * `-I` alone is honoured;
  * `-I` and RITZ_PATH MERGE (gcc-style: -I first), not override;
  * with neither, the import fails, which shows the other three really go
    through the search path and are not found some other way.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

HELPER = """\
pub fn helper_1750() -> i32
    42
"""

# Imports only the helper: nothing from ritzlib, so RITZ_ROOT is not needed.
MAIN_HELPER_ONLY = """\
import helper_1750

fn main() -> i32
    helper_1750() - 42
"""

# Needs BOTH search entries: the helper (via one) and ritzlib (via the other).
MAIN_HELPER_AND_RITZLIB = """\
import ritzlib.sys
import helper_1750

fn main() -> i32
    helper_1750() - 42
"""


@pytest.fixture
def layout(tmp_path):
    """tmp/src/main.ritz plus tmp/lib/helper_1750.ritz, in separate dirs."""
    src_dir = tmp_path / "src"
    lib_dir = tmp_path / "lib"
    src_dir.mkdir()
    lib_dir.mkdir()
    (lib_dir / "helper_1750.ritz").write_text(HELPER)
    return src_dir, lib_dir


def _compile(ritz1_bin, src_dir, program, ritz_path=None, dash_i=None):
    main = src_dir / "main.ritz"
    main.write_text(program)
    env = {k: v for k, v in os.environ.items() if k != "RITZ_PATH"}
    if ritz_path is not None:
        env["RITZ_PATH"] = ritz_path
    cmd = [str(ritz1_bin), str(main), "-o", str(src_dir / "main.ll")]
    if dash_i is not None:
        cmd += ["-I", str(dash_i)]
    # cwd is the source dir, which holds no helper: only the search path does.
    return subprocess.run(
        cmd, cwd=src_dir, env=env, capture_output=True, text=True, timeout=300
    )


def _detail(proc):
    return f"stdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}"


def test_ritz_path_env_multi_entry(ritz1_bin, layout):
    src_dir, lib_dir = layout
    proc = _compile(
        ritz1_bin,
        src_dir,
        MAIN_HELPER_AND_RITZLIB,
        ritz_path=f"{lib_dir}:{RITZ_ROOT}",
    )
    assert proc.returncode == 0, _detail(proc)


def test_dash_i_alone(ritz1_bin, layout):
    src_dir, lib_dir = layout
    proc = _compile(ritz1_bin, src_dir, MAIN_HELPER_ONLY, dash_i=lib_dir)
    assert proc.returncode == 0, _detail(proc)


def test_dash_i_merges_with_ritz_path_env(ritz1_bin, layout):
    # The helper is only reachable through -I and ritzlib only through
    # RITZ_PATH: either one overriding the other fails the compile.
    src_dir, lib_dir = layout
    proc = _compile(
        ritz1_bin,
        src_dir,
        MAIN_HELPER_AND_RITZLIB,
        ritz_path=str(RITZ_ROOT),
        dash_i=lib_dir,
    )
    assert proc.returncode == 0, _detail(proc)


def test_no_search_path_cannot_find_helper(ritz1_bin, layout):
    src_dir, _lib_dir = layout
    proc = _compile(ritz1_bin, src_dir, MAIN_HELPER_ONLY)
    assert proc.returncode != 0, (
        "ritz1 found a module outside the source dir with no RITZ_PATH and "
        "no -I, so the tests above prove nothing about the search path:\n"
        + _detail(proc)
    )
