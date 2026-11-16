"""AGAST #3726: an imported `async fn` is declared, not defined, in its importer.

    # a.ritz                          # main.ritz
    pub async fn fetch(x: i32) -> i32 import a
        x + 1                         async fn main() -> i32
                                          await fetch(41)

`_transform_async_functions` runs over the merged module, imports included.
The constructor (`fetch`) and poll fn (`fetch_poll`) it generated for an
imported async fn did not carry the original's `source_file`, so the importer
emitted their bodies as well as a.ritz's own object did: the link failed with
"multiple definition of `fetch'".  (54_async_fs, the corpus' only importer of
ritzlib.async.blocking_fs, was the program that hit it.)

ritz0 only: ritz1 has no async fns (ritz1/src/main.ritz).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent

A_SRC = "pub async fn fetch(x: i32) -> i32\n    x + 1\n"
MAIN_SRC = "import a\n\nasync fn main() -> i32\n    await fetch(41)\n"


def _compile(tmp_path, name, *extra):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    proc = run_ritz0([f"{name}.ritz", "-o", str(ll), *extra],
                     cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return ll


def test_imported_async_fn_links_and_runs(tmp_path):
    (tmp_path / "a.ritz").write_text(A_SRC)
    (tmp_path / "main.ritz").write_text(MAIN_SRC)
    main_ll = _compile(tmp_path, "main")
    # Only the main object may carry a _start.
    a_ll = _compile(tmp_path, "a", "--no-runtime")

    # The importer declares fetch's constructor and poll fn; a.ritz defines them.
    lines = main_ll.read_text().splitlines()
    for sym in ("fetch", "fetch_poll"):
        heads = [l for l in lines if re.search(rf'@"?{sym}"?\(', l)
                 and l.startswith(("define", "declare"))]
        assert heads and all(l.startswith("declare") for l in heads), (sym, heads)

    exe = tmp_path / "main"
    link = fast_link.clang(["clang", "-Wno-override-module", str(main_ll), str(a_ll),
                            "-o", str(exe), "-nostdlib", "-no-pie"],
                           capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-3000:]
    assert subprocess.run([str(exe)], capture_output=True, timeout=60).returncode == 42
