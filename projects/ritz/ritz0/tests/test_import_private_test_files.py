"""AGAST #4030: #3891's check holds for every file of a test suite alone.

`rz test` builds each test file's binary in turn, and in one process (build.py
runs test_runner.run_files in-process; `ritz0 --test a b` does the same for a
list). ritz-task-3917 reported that ritz1 accepted valet's test_tls.ritz using
a type it never imported only while another test file of the package was in
the suite, as if a name made visible by one file's compile leaked into the
next. The shape, in one package:

    src/m.ritz      declares Sm
    src/lib.ritz    plain `import m`
    test/test_a     `import m`, uses Sm: fine
    test/test_b     `import lib` only, uses Sm (sizeof, valet's shape): #3891

test_a runs first (the leak's order), and test_b must still be refused, with
test_a passing. ritz0 is the oracle: all three compilers give one verdict.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

MANIFEST = """\
[package]
name = "leak4030"
version = "0.1.0"
sources = ["src"]

[[bin]]
name = "leak4030"
entry = "main::main"
"""

FILES = {
    "src/m.ritz": """\
pub struct Sm
    v: i32
""",
    "src/lib.ritz": """\
import m

pub fn lib_id(x: i32) -> i32
    x
""",
    "src/main.ritz": """\
import lib

fn main() -> i32
    lib_id(0)
""",
    # Imports m: Sm is its own to use.
    "test/test_a.ritz": """\
import m

[[test]]
fn test_a() -> i32
    var s: Sm = Sm { v: 3 }
    assert s.v == 3
    assert sizeof(Sm) == 4
    0
""",
    # Reaches m only through lib's plain import.
    "test/test_b.ritz": """\
import lib

[[test]]
fn test_b() -> i32
    assert sizeof(Sm) == 4
    lib_id(0)
""",
}


def _package(tmp_path: Path) -> Path:
    pkg = tmp_path / "leak4030"
    (pkg / "src").mkdir(parents=True)
    (pkg / "test").mkdir()
    (pkg / "ritz.toml").write_text(MANIFEST)
    for rel, text in FILES.items():
        (pkg / rel).write_text(text)
    return pkg


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_name_another_test_file_imports_stays_hidden(tmp_path, compiler):
    if compiler != "ritz0":
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries first.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    pkg = _package(tmp_path)
    cmd = [
        sys.executable,
        str(RITZ_ROOT / "ritz0" / "ritz0.py"),
        "--test",
        "test/test_a.ritz",
        "test/test_b.ritz",
    ]
    if compiler != "ritz0":
        cmd += ["--compiler", compiler]
    proc = subprocess.run(
        cmd,
        cwd=pkg,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out[-3000:]
    # test_a built and passed first; test_b, after it, did not build.
    assert "1 passed, 0 failed, 1 errored" in proc.stdout, out[-3000:]
    errors = [ln for ln in proc.stderr.splitlines() if ln.startswith("Error in ")]
    assert len(errors) == 1, out[-3000:]
    assert errors[0].startswith("Error in test_b.ritz: "), errors
    assert (
        "`Sm` is undefined (#3891): it comes from `m`; import it, or have `lib` `pub import` it"
        in errors[0]
    ), errors
