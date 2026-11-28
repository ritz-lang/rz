"""`ritz1 main.ritz`, a source path with no directory part, resolves a
sibling import from the current directory (AGAST #4934).

`path_dir` returned "" for a bare filename, and `try_open_import` treated an
empty source dir as "nothing to probe", so

    cd pkg && ritz1 main.ritz -o m.ll     # import a  (pkg/a.ritz)

failed with "Could not read import: a.ritz" while `ritz1 ./main.ritz` and
ritz0 compiled it.  tools/refusal_parity.py replays exactly that way, so
every multi-file reject-parity row read the import error instead of the rule.
A bare path's directory is now "./", as ritz0's ImportResolver probes
`<cwd>/a.ritz`; the module-IR cache's fingerprint takes the same directory.
A hit under a relative source dir is named by its realpath, as ritz0 names
every import (`./a.ritz:1:1: note` was ritz1's, `/abs/a.ritz:1:1` ritz0's).

Rows: the bare spelling on both ritz1 builds (the ticket's repro), and the
`./` spelling as the control that always worked.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.integration

MODULE_A = "pub fn k() -> i32\n    3\n"
MAIN = "import a\n\nfn main() -> i32\n    k()\n"


@pytest.fixture(params=["ritz1", "ritz1_selfhosted"])
def compiler(request) -> Path:
    return request.getfixturevalue(request.param + ("_bin" if request.param == "ritz1" else ""))


@pytest.mark.parametrize("spelling", ["main.ritz", "./main.ritz"])
def test_sibling_import_resolves_from_cwd(compiler, spelling, tmp_path):
    (tmp_path / "a.ritz").write_text(MODULE_A)
    (tmp_path / "main.ritz").write_text(MAIN)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT), RITZ_CACHE_DIR=str(tmp_path / "cache"))
    proc = subprocess.run([str(compiler), spelling, "-o", "m.ll"], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "define i32 @main" in (tmp_path / "m.ll").read_text()


@pytest.mark.parametrize("spelling", ["main.ritz", "./main.ritz"])
def test_import_found_from_cwd_is_named_by_its_realpath(compiler, spelling, tmp_path):
    """A note in the import names it as ritz0 does, by its realpath, not `./a.ritz`."""
    (tmp_path / "a.ritz").write_text("fn k() -> i32\n    3\n")
    (tmp_path / "main.ritz").write_text(MAIN)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT), RITZ_CACHE_DIR=str(tmp_path / "cache"))
    proc = subprocess.run([str(compiler), spelling, "-o", "m.ll"], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode != 0
    notes = [l for l in proc.stderr.splitlines() if ": note: " in l]
    assert notes == [f"{(tmp_path / 'a.ritz').resolve()}:1:1: note: `k` is declared here"]
