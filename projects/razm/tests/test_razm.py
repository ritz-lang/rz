"""razm against the oracle, file by file (DESIGN.md "What razm checks").

razm exits 2 for a file holding a construct it does not accept yet. That
file's comparison is an expected failure naming the file, never a pass and
never a skip. Any other non-zero exit is a failure.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from oracle import (CORPUS_FILES, KERNEL_FILES, assemble, assemble_with_as,
                    compare_files, compare_links, link_kernel)

PKG = Path(__file__).resolve().parent.parent
EXIT_UNSUPPORTED = 2


@pytest.fixture(scope="module")
def razm() -> list[str]:
    """The razm under test: $RAZM, else this package's debug build."""
    path = Path(os.environ.get("RAZM") or PKG / "build" / "debug" / "razm")
    if not os.access(path, os.X_OK):
        pytest.fail(f"razm is not built at {path}: run ./rz build razm first")
    return [str(path)]


def _assemble_razm(razm, rel: str, out: Path) -> str | None:
    """None if razm wrote `out`; the reason if it does not accept `rel` yet."""
    r = assemble(razm, rel, out)
    if r.returncode == EXIT_UNSUPPORTED:
        return r.stderr.strip()
    assert r.returncode == 0, f"razm {rel}: exit {r.returncode}: {r.stderr}"
    return None


@pytest.mark.parametrize("rel", CORPUS_FILES)
def test_razm_matches_as(razm, rel, tmp_path):
    want, got = tmp_path / "as.o", tmp_path / "razm.o"
    assemble_with_as(rel, want)
    unsupported = _assemble_razm(razm, rel, got)
    if unsupported is not None:
        pytest.xfail(f"razm does not assemble {rel} yet: {unsupported}")
    assert compare_files(want, got) == []


def test_razm_kernel_link_matches_as(razm, tmp_path):
    as_objs, razm_objs, pending = [], [], []
    for rel in KERNEL_FILES:
        stem = rel.replace("/", "__").removesuffix(".s")
        as_obj, razm_obj = tmp_path / f"{stem}.as.o", tmp_path / f"{stem}.razm.o"
        assemble_with_as(rel, as_obj)
        if _assemble_razm(razm, rel, razm_obj) is not None:
            pending.append(rel)
        as_objs.append(as_obj)
        razm_objs.append(razm_obj)
    if pending:
        pytest.xfail(f"razm does not assemble {', '.join(pending)} yet")
    want, got = tmp_path / "as.elf", tmp_path / "razm.elf"
    link_kernel(as_objs, want)
    link_kernel(razm_objs, got)
    assert compare_links(want, got) == []


@pytest.mark.parametrize("argv, message", [
    (["--32", "-o", "x.o", "kernel/boot.s"], "--32 is not supported"),
    (["-o", "x.o", "kernel/boot.s"], "--64 is required"),
    (["--64", "kernel/boot.s"], "-o OUT is required"),
    (["--64", "-o", "x.o"], "no input file"),
    (["--64", "-o", "x.o", "-q", "kernel/boot.s"], "unknown option"),
    (["--64", "-o", "x.o", "no/such/file.s"], "cannot read file"),
])
def test_razm_cli_errors_exit_1(razm, tmp_path, argv, message):
    p = subprocess.run([*razm, *argv], cwd=Path(__file__).parent / "corpus",
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 1, p
    assert message in p.stderr
