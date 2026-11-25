"""AGAST #3737: ritzlib.os.env reads the environment `_start` was handed.

os/env used to read only /proc/self/environ.  Once a process is not dumpable
(prctl(PR_SET_DUMPABLE, 0), or a setuid/setgid/cap-changing exec) the kernel
makes /proc/self/* root-owned, the open fails with EACCES, and env_load
silently cached an EMPTY environment: env_get returned None and exec'd
children got an empty env.  #3725 only fixed ritzunit's children.

Every `_start` now stores the kernel's envp in one global, `__ritz_envp`, and
os/env reads that first, with /proc/self/environ as the fallback:

  - ritz0 emits `_start` inline (both main shapes, and test mode);
  - ritz1 emits one in test mode;
  - runtime/*.ll are the shims build.py and ritz1's links use.

The rows, each able to fail on its own:

  - build.py packages that drop dumpable, then env_get("PATH"): ritz0,
    ritz1 and ritz1_selfhosted, and ritz0 with a Span main (the adapter);
  - single-file programs that read `__ritz_envp` directly: ritz0's inline
    `_start` per main shape, and ritz1 linked with each Linux shim;
  - every runtime/*.ll, Harland's included (they can't run here), stores it.
"""

import os
import subprocess
import sys
from pathlib import Path

import fast_link
import pytest
from ritz0_inproc import run_ritz0

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from build import ensure_runtime_object

RITZ_ROOT = Path(__file__).resolve().parents[2]
RUNTIME = RITZ_ROOT / "runtime"
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

# A variable only this test sets, so a hit can't come from anywhere else.
MARKER = "RZ3737=yes"


# --- build.py packages: drop dumpable, then read the environment ------------

# `()` is the C symbol `_start` calls; a Span main goes through the adapter
# (main_abi.py). C's argc/argv shapes are refused since #204.
MAINS = {
    0: "pub fn main() -> i32",
    2: "pub fn main(args: Span<StrView>, env: Span<StrView>) -> i32",
}

NONDUMPABLE = """\
import ritzlib.sys
import ritzlib.option
import ritzlib.strview
import ritzlib.os.env

const SYS_PRCTL: i64 = 157
const PR_SET_DUMPABLE: i64 = 4

@MAIN@
    if syscall2(SYS_PRCTL, PR_SET_DUMPABLE, 0) != 0
        return 2
    # The precondition: /proc/self/environ is now closed to us.
    let fd: i32 = sys_open(c"/proc/self/environ", 0)
    if fd >= 0
        sys_close(fd)
        return 3
    if env_iter().len == 0
        return 4
    match env_get("PATH")
        Some(v) =>
            sys_write(1, v.ptr, v.len)
            0
        None => 1
"""


def _build_pkg(compiler: str, tmp_path: Path, name: str, program: str) -> Path:
    pkg = tmp_path / f"{name}_{compiler}"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text(program)
    (pkg / "ritz.toml").write_text(
        f'[package]\nname = "{name}"\nversion = "0.1.0"\n'
    )
    # AGAST #2793: the session's content-addressed store supplies ritzlib's
    # objects; the per-project index stays in the package.
    env = dict(
        os.environ,
        RITZ_PATH=str(RITZ_ROOT),
        RITZ_BUILD_CACHE_DIR=str(pkg / ".build-cache"),
    )
    proc = subprocess.run(
        [
            sys.executable,
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
        check=False,
    )
    exe = pkg / "build" / "debug" / name
    assert proc.returncode == 0 and exe.exists(), (
        f"{compiler} failed to build {name}:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    )
    return exe


@pytest.mark.integration
@pytest.mark.parametrize(
    "compiler,arity",
    [
        ("ritz0", 0),
        ("ritz0", 2),
        ("ritz1", 0),
        ("ritz1_selfhosted", 0),
    ],
)
def test_env_get_after_dropping_dumpable(request, tmp_path, compiler, arity):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    if os.geteuid() == 0:
        pytest.skip("root can read a non-dumpable process's /proc/self/environ")
    exe = _build_pkg(
        compiler,
        tmp_path,
        f"nodump{arity}",
        NONDUMPABLE.replace("@MAIN@", MAINS[arity]),
    )
    run = subprocess.run(
        [str(exe)],
        capture_output=True,
        timeout=60,
        env=dict(os.environ, PATH=os.environ["PATH"]),
        check=False,
    )
    assert run.returncode != 3, "/proc/self/environ still readable: nothing tested"
    assert run.returncode == 0, (
        f"exit {run.returncode}: env empty after PR_SET_DUMPABLE=0"
    )
    assert run.stdout.decode() == os.environ["PATH"]


# --- single-file programs: `_start` itself sets __ritz_envp ------------------

READS_GLOBAL = """\
extern var __ritz_envp: **u8

fn has_marker(envp: **u8) -> i32
    var i: i64 = 0
    while *(envp + i) != null
        let e: *u8 = *(envp + i)
        if *e == 'R' and *(e + 1) == 'Z' and *(e + 2) == '3' and *(e + 3) == '7' and *(e + 4) == '3' and *(e + 5) == '7' and *(e + 6) == '='
            return 1
        i = i + 1
    return 0

@MAIN@
    if __ritz_envp == null
        return 2
    if has_marker(__ritz_envp) == 0
        return 3
@CHECK_ENVP@    return 0
"""

# main's `env` views the strings `_start` stored.
SAME_AS_ENVP = "    if env.len == 0 or env[0].ptr != *__ritz_envp\n        return 4\n"

def _reads_global(arity: int) -> str:
    return READS_GLOBAL.replace("@MAIN@", MAINS[arity]).replace(
        "@CHECK_ENVP@", SAME_AS_ENVP if arity == 2 else ""
    )


def _shim(name: str) -> Path:
    obj = RUNTIME / f"{name}.x86_64.o"
    assert ensure_runtime_object(obj), f"could not build {obj}"
    return obj


def _compile_link_run(
    request, tmp_path: Path, compiler: str, program: str, objs=(), no_runtime=False
) -> int:
    src = tmp_path / "main.ritz"
    src.write_text(program)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        args = [str(src), "-o", str(ll)] + (["--no-runtime"] if no_runtime else [])
        comp = run_ritz0(args, cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        comp = subprocess.run(
            [str(RITZ1_BUILD / compiler), str(src), "-o", str(ll)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    assert comp.returncode == 0 and ll.exists(), (
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / "main"
    link = fast_link.clang(
        ["clang", "-w", *map(str, objs), str(ll), "-o", str(exe), "-nostdlib"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert link.returncode == 0, link.stderr[-2000:]
    return subprocess.run(
        [str(exe)],
        env=dict(os.environ, RZ3737="yes"),
        capture_output=True,
        timeout=60,
        check=False,
    ).returncode


@pytest.mark.integration
@pytest.mark.parametrize("arity", sorted(MAINS))
def test_ritz0_inline_start_sets_ritz_envp(request, tmp_path, arity):
    assert _compile_link_run(request, tmp_path, "ritz0", _reads_global(arity)) == 0


@pytest.mark.integration
@pytest.mark.parametrize("arity", sorted(MAINS))
def test_linux_shim_sets_ritz_envp(request, tmp_path, arity):
    """One `_start` for every shape of `main` (AGAST #200)."""
    rc = _compile_link_run(
        request, tmp_path, "ritz1", _reads_global(arity), objs=[_shim("ritz_start")]
    )
    assert rc == 0


@pytest.mark.parametrize("shim", sorted(p.name for p in RUNTIME.glob("*.ll")))
def test_every_runtime_shim_stores_ritz_envp(shim):
    """Harland's shims can't run here; each must at least store the global."""
    text = (RUNTIME / shim).read_text()
    assert "__ritz_envp(%rip)" in text, f"{shim}'s _start never stores __ritz_envp"
    assert "@__ritz_envp = weak global" in text, f"{shim} doesn't define __ritz_envp"
