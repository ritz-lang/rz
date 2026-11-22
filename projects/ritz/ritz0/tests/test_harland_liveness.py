"""Every kernel/src module is reachable from kernel_main (AGAST #1886).

`rz build harland` compiles only the import closure, so an unimported module
never compiles and cannot fail a build. `projects/harland/tools/check_liveness.py`
walks the same closure (ritz0/list_deps.py, the resolver build.py uses) and
fails on an orphan module; this pins it into the gate and proves it catches a
planted orphan.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
HARLAND = RITZ_ROOT.parent / "harland"
CHECK = HARLAND / "tools" / "check_liveness.py"

pytestmark = pytest.mark.integration


def _check(package: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CHECK), "--package", str(package)],
                          capture_output=True, text=True, timeout=120)


def test_every_kernel_module_is_reachable():
    proc = _check(HARLAND)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "0 orphaned" in proc.stdout, proc.stdout
    # mm/dma's exemption is explicit and counted, not silently skipped.
    assert "1 allowlisted" in proc.stdout, proc.stdout


def test_liveness_check_catches_a_planted_orphan(tmp_path):
    package = tmp_path / "fixture"
    (package / "src").mkdir(parents=True)
    (package / "src" / "main.ritz").write_text(
        "import live\n\nfn main() -> i32\n    live_value()\n")
    (package / "src" / "live.ritz").write_text(
        "pub fn live_value() -> i32\n    1\n")
    (package / "src" / "orphan.ritz").write_text(
        "pub fn orphan_value() -> i32\n    2\n")
    (package / "ritz.toml").write_text(textwrap.dedent("""\
        [package]
        name = "fixture"
        sources = ["src"]

        [[bin]]
        name = "fixture"
        entry = "main::main"
        target = "x86_64-none-elf"
        freestanding = true
        """))

    proc = _check(package)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "orphan.ritz" in proc.stderr, proc.stderr
    assert "live.ritz" not in proc.stderr, proc.stderr
