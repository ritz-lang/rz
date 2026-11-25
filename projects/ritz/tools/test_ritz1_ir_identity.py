"""ritz1_ir_identity: the tool that holds an emitter refactor to byte-identical IR.

Fake compilers (shell scripts) stand in for ritz1, so the test needs no build.
Each mutation of the candidate must turn exactly its own case red.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

import ritz1_ir_identity as ident

pytestmark = pytest.mark.integration


def fake_compiler(path: Path, body: str) -> Path:
    # $1 is the source, $3 the output; `body` sees both.
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    for rel in ("ritz0/test/a.ritz", "ritzlib/b.ritz", "ritz1/src/c.ritz"):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("fn main() -> i32\n    0\n")
    return root


COPY = 'cp "$1" "$3"'


def run(tmp_path: Path, cand_body: str, capsys) -> tuple[int, str]:
    root = make_root(tmp_path)
    ref = fake_compiler(tmp_path / "ref", COPY)
    cand = fake_compiler(tmp_path / "cand", cand_body)
    rc = ident.main(["--ref", str(ref), "--cand", str(cand), "--root", str(root), "--jobs", "2"])
    return rc, capsys.readouterr().out


def test_identical_compilers_pass(tmp_path, capsys):
    rc, out = run(tmp_path, COPY, capsys)
    assert rc == 0
    assert "3/3 modules identical" in out


def test_one_differing_module_is_named_and_fails(tmp_path, capsys):
    body = 'cp "$1" "$3"; case "$1" in */ritzlib/b.ritz) echo extra >> "$3";; esac'
    rc, out = run(tmp_path, body, capsys)
    assert rc == 1
    assert "DIFF ritzlib/b.ritz: IR differs" in out
    assert "DIFF ritz0" not in out and "DIFF ritz1" not in out


def test_a_changed_exit_status_is_a_difference(tmp_path, capsys):
    body = 'case "$1" in */c.ritz) exit 3;; esac; cp "$1" "$3"'
    rc, out = run(tmp_path, body, capsys)
    assert rc == 1
    assert "DIFF ritz1/src/c.ritz: exit status 0 (reference) vs 3 (candidate)" in out


def test_both_refusing_with_the_same_diagnostics_agree(tmp_path, capsys):
    root = make_root(tmp_path)
    both = fake_compiler(tmp_path / "both", 'echo "no" >&2; exit 1')
    rc = ident.main(["--ref", str(both), "--cand", str(both), "--root", str(root)])
    assert rc == 0
    assert "3/3 modules identical" in capsys.readouterr().out


def test_both_refusing_with_different_diagnostics_differ(tmp_path, capsys):
    root = make_root(tmp_path)
    a = fake_compiler(tmp_path / "a", 'echo "no" >&2; exit 1')
    b = fake_compiler(tmp_path / "b", 'echo "nope" >&2; exit 1')
    rc = ident.main(["--ref", str(a), "--cand", str(b), "--root", str(root)])
    assert rc == 1
    assert "diagnostics differ" in capsys.readouterr().out


def test_each_compile_gets_an_empty_cache(tmp_path, capsys):
    # The compiler writes its cache dir's listing into the IR: a shared or
    # warm cache would show up as a difference between the two runs.
    body = 'ls "$RITZ_CACHE_DIR" 2>/dev/null > "$3"; mkdir -p "$RITZ_CACHE_DIR"; touch "$RITZ_CACHE_DIR/warm"'
    root = make_root(tmp_path)
    c = fake_compiler(tmp_path / "c", body)
    rc = ident.main(["--ref", str(c), "--cand", str(c), "--root", str(root)])
    assert rc == 0


def test_missing_binary_is_a_setup_error(tmp_path):
    root = make_root(tmp_path)
    assert ident.main(["--ref", str(tmp_path / "none"), "--cand", str(tmp_path / "none"), "--root", str(root)]) == 2


def test_empty_corpus_is_a_setup_error(tmp_path):
    c = fake_compiler(tmp_path / "c", COPY)
    assert ident.main(["--ref", str(c), "--cand", str(c), "--root", str(tmp_path / "empty")]) == 2
