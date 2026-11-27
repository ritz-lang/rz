"""razm against the oracle, file by file (DESIGN.md "What razm checks").

Every corpus file and synthetic fixture must assemble and match. razm exits 2
for a construct outside its dialect and 1 for any other failure; stderr names
FILE:LINE and the construct.
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

# Fixtures beyond DESIGN.md's corpus, one per driver rule: alignment fill,
# branch sizing, and relocation selection.
SYNTHETIC_FILES = ["synthetic/fill.s", "synthetic/fill_end16.s",
                   "synthetic/relax.s", "synthetic/relocs.s"]


@pytest.fixture(scope="module")
def razm() -> list[str]:
    """The razm under test: $RAZM, else this package's debug build."""
    path = Path(os.environ.get("RAZM") or PKG / "build" / "debug" / "razm")
    if not os.access(path, os.X_OK):
        pytest.fail(f"razm is not built at {path}: run ./rz build razm first")
    return [str(path)]


def _assemble_razm(razm, rel: str, out: Path) -> None:
    r = assemble(razm, rel, out)
    assert r.returncode == 0, f"razm {rel}: exit {r.returncode}: {r.stderr}"


@pytest.mark.parametrize("rel", CORPUS_FILES + SYNTHETIC_FILES)
def test_razm_matches_as(razm, rel, tmp_path):
    want, got = tmp_path / "as.o", tmp_path / "razm.o"
    assemble_with_as(rel, want)
    _assemble_razm(razm, rel, got)
    assert compare_files(want, got) == []


def test_razm_kernel_link_matches_as(razm, tmp_path):
    as_objs, razm_objs = [], []
    for rel in KERNEL_FILES:
        stem = rel.replace("/", "__").removesuffix(".s")
        as_obj, razm_obj = tmp_path / f"{stem}.as.o", tmp_path / f"{stem}.razm.o"
        assemble_with_as(rel, as_obj)
        _assemble_razm(razm, rel, razm_obj)
        as_objs.append(as_obj)
        razm_objs.append(razm_obj)
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


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_razm_help_prints_usage_to_stdout_and_exits_0(razm, flag):
    # The stack smoke runs every [[bin]] with --help and needs exit 0.
    p = subprocess.run([*razm, flag], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p
    assert "Usage: razm --64 -o OUT FILE.s" in p.stdout
    assert p.stderr == ""


@pytest.mark.parametrize("source, line, message, status", [
    ("start:\n.rept 200\nnop\n.endr\nloop start\n", 5, "out of range", 1),
    ("nop\nfrobq %rax\n", 2, "frobq", EXIT_UNSUPPORTED),
    ("movb $300, %al\n", 1, "immediate", EXIT_UNSUPPORTED),
    (".byte 1\nlabel:\n.long label + undefined_sym\n", 3, "two symbols", 1),
])
def test_razm_errors_name_file_line_and_construct(razm, tmp_path, source, line,
                                                   message, status):
    src = tmp_path / "bad.s"
    src.write_text(source)
    p = subprocess.run([*razm, "--64", "-o", str(tmp_path / "bad.o"), "bad.s"],
                       cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert p.returncode == status, p
    assert f"bad.s:{line}:" in p.stderr, p.stderr
    assert message in p.stderr, p.stderr
    assert not (tmp_path / "bad.o").exists()
