"""The cutover survey (survey.py; DESIGN.md "Coverage before the switch"):
one verdict per `.ll` under DIR, a construct tally, the counts, and an exit
status that fails only on a file rllvm could neither compile nor reject."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SURVEY = Path(__file__).resolve().parent / "survey.py"

GOOD = "define i32 @f() {\nentry:\n  ret i32 0\n}\n"
LAYOUT = 'target datalayout = "e-m:e-i64:64"\n' + GOOD
UEFI = 'target triple = "x86_64-unknown-uefi"\n' + GOOD
MALFORMED = "define i32 @f( {\n"


def survey(rllvm_bin, root: Path, *argv: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "RLLVM": rllvm_bin}
    return subprocess.run([sys.executable, str(SURVEY), str(root), *argv],
                          capture_output=True, text=True, env=env, timeout=120, check=False)


def tree(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


def test_each_file_gets_its_verdict_and_the_counts(rllvm_bin, tmp_path):
    root = tree(tmp_path, {"a.ll": GOOD, "sub/b.ll": LAYOUT, "sub/deep/c.ll": GOOD,
                           "notes.txt": "not ir", "d.o": ""})
    p = survey(rllvm_bin, root)
    assert p.returncode == 0, p
    lines = p.stdout.splitlines()
    assert "accepted  a.ll" in lines
    assert "accepted  sub/deep/c.ll" in lines
    assert "rejected  sub/b.ll:1  target datalayout 'e-m:e-i64:64'" in lines
    assert lines[-1] == f"survey {root} (hosted): 3 files: 2 accepted, 1 rejected, 0 failed"


def test_constructs_are_tallied_most_files_first(rllvm_bin, tmp_path):
    root = tree(tmp_path, {"a.ll": LAYOUT, "b.ll": LAYOUT, "c.ll": UEFI})
    p = survey(rllvm_bin, root)
    tally = p.stdout.split("rejected constructs:\n")[1].splitlines()[:2]
    assert tally == ["     2  target datalayout 'e-m:e-i64:64'",
                     "     1  target triple 'x86_64-unknown-uefi'"]


def test_a_failed_file_fails_the_survey(rllvm_bin, tmp_path):
    root = tree(tmp_path, {"a.ll": GOOD, "bad.ll": MALFORMED})
    p = survey(rllvm_bin, root)
    assert p.returncode == 1, p
    assert any(ln.startswith("failed    bad.ll  exit 1: rllvm: ")
               for ln in p.stdout.splitlines()), p.stdout
    assert p.stdout.splitlines()[-1].endswith("1 accepted, 0 rejected, 1 failed")


def test_the_profile_picks_rllvms_flags(rllvm_bin, tmp_path):
    # kernel's argv carries --target=x86_64-none-elf, which overrides the
    # module's UEFI triple exactly as it does for clang.
    root = tree(tmp_path, {"u.ll": UEFI})
    assert "rejected  u.ll:1  target triple" in survey(rllvm_bin, root).stdout
    p = survey(rllvm_bin, root, "--profile", "kernel")
    assert p.returncode == 0, p
    assert "accepted  u.ll" in p.stdout.splitlines()
    assert "(kernel): 1 files: 1 accepted" in p.stdout


def test_no_ll_files_is_an_error(rllvm_bin, tmp_path):
    p = survey(rllvm_bin, tree(tmp_path, {"x.s": ""}))
    assert p.returncode == 1, p
    assert "no .ll files" in p.stderr


@pytest.mark.parametrize("argv, message", [
    (["--profile", "medium"], "invalid choice: 'medium'"),
])
def test_usage_errors(rllvm_bin, tmp_path, argv, message):
    p = survey(rllvm_bin, tmp_path, *argv)
    assert p.returncode != 0 and message in p.stderr, p


def test_missing_dir_is_an_error(rllvm_bin, tmp_path):
    p = survey(rllvm_bin, tmp_path / "nope")
    assert p.returncode == 1 and "not a directory" in p.stderr, p


def test_it_compiles_nothing_into_dir(rllvm_bin, tmp_path):
    root = tree(tmp_path, {"a.ll": GOOD})
    survey(rllvm_bin, root)
    assert sorted(p.name for p in root.iterdir()) == ["a.ll"]
