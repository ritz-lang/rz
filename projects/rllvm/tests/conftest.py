"""The binaries under test: $RLLVM / $RLLVM_IR, else this package's debug build."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parent.parent


def _binary(env: str, name: str) -> str:
    path = Path(os.environ.get(env) or PKG / "build" / "debug" / name)
    if not os.access(path, os.X_OK):
        pytest.fail(f"{name} is not built at {path}: run ./rz build rllvm first")
    return str(path)


@pytest.fixture(scope="session")
def rllvm_bin() -> str:
    return _binary("RLLVM", "rllvm")


@pytest.fixture(scope="session")
def rllvm_ir_bin() -> str:
    return _binary("RLLVM_IR", "rllvm-ir")


def run(argv: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=60)
