"""AGAST #4608: a generic's instance, emitted in a test file's harness, calls
its own module's private fn, and the test binary links.

    # lib/a.ritz                       # t.ritz
    fn helper(x: i32) -> i32           import lib.a { wrap }
        x + 1                          [[test]]
    pub fn wrap<T>(v: T, x: i32) -> i32    fn test_wrap() -> i32
        helper(x)                          assert wrap<i64>(5, 41) == 42

`wrap$i64` is emitted in the harness's object. lib/a.ritz's object
(`--no-runtime`) exports the private `helper` under its file-qualified symbol
(AGAST #1858), so the harness must call that symbol too. Under ritz0 the
harness is compiled with the runtime, where a private fn was declared by its
bare name: `undefined reference to 'helper'`. #4356 fixed the same call
between two `--no-runtime` objects (test_private_fn_no_clash.py).

The private fn stays private: `import lib.a { helper }` is still refused.

Each case runs ritz0 and both ritz1 binaries through test_runner's real
`--test` build (build_test_binary), as `ritz0 --test` and `rz test` do.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

LIB_A = """\
fn helper(x: i32) -> i32
    x + 1

pub fn wrap<T>(v: T, x: i32) -> i32
    helper(x)
"""

TEST_FILE = """\
import lib.a { wrap }

[[test]]
fn test_wrap() -> i32
    assert wrap<i64>(5, 41) == 42
    0
"""


def _write(tmp_path: Path, test_src: str) -> Path:
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "a.ritz").write_text(LIB_A)
    src = tmp_path / "t.ritz"
    src.write_text(test_src)
    return src


@pytest.mark.parametrize("compiler", COMPILERS)
def test_instance_in_test_harness_calls_its_modules_private_fn(
        compiler, tmp_path, monkeypatch):
    """The acceptance case: the test binary links and its test passes."""
    if compiler != "ritz0":
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert (RITZ1_BUILD / compiler).exists(), \
            f"{compiler} missing; run `make -C ritz1 bootstrap`"
    sys.path.insert(0, str(RITZ_ROOT / "ritz0"))
    import test_runner

    monkeypatch.setenv("RITZ_PATH", f"{tmp_path}:{RITZ_ROOT}")
    # A private, empty artifact store: nothing served from another run.
    monkeypatch.setenv("RITZ_CACHE_DIR", str(tmp_path / "cas"))
    src = _write(tmp_path, TEST_FILE)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    exe, error = test_runner.build_test_binary(str(src), str(scratch), compiler)
    assert error is None, f"{compiler}: {error}"
    run = subprocess.run([exe, *test_runner.runner_args()],
                         capture_output=True, timeout=60)
    report = json.loads(run.stdout)
    status = {t["name"]: t["status"] for t in report["tests"]}
    assert run.returncode == 0 and status == {"test_wrap": "pass"}, run


@pytest.mark.parametrize("compiler", COMPILERS)
def test_selective_import_of_the_private_fn_is_still_refused(compiler, tmp_path):
    """Its symbol reaches the instance; its name is not importable (§15.2)."""
    src = _write(tmp_path, "import lib.a { helper }\n\n"
                           "fn main() -> i32\n    0\n")
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    args = [str(src), "-o", str(tmp_path / "t.ll")]
    if compiler == "ritz0":
        proc = run_ritz0(args + ["--no-runtime"], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary)] + args, cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    out = proc.stderr + proc.stdout
    assert proc.returncode != 0, f"{compiler} accepted `import lib.a {{ helper }}`:\n{out}"
    assert "`helper` is private to a.ritz" in out, out
