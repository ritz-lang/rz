#!/usr/bin/env python3
"""An `import M as A` alias must not crash on a single-expression match arm.

Found by AGAST #1472. ImportResolver rewrites `A.f(...)` to `f(...)` in every
module a program with an alias import reaches, and it walked each match arm's
body with _transform_block, which assumes a Block. A body such as `Some(_) => 1`
is an IntLit, so ritz0 died with

    AttributeError: 'IntLit' object has no attribute 'stmts'

before emitting anything. ritzlib/option.ritz is written in that style, so
`import ritzlib.sys as sys` plus anything that reaches ritzlib.option (after
#1472 that includes ritzlib.io, through strview) failed to compile.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# xdist_group("tree") (AGAST #1804): `build.py run` writes projects/ritz/build/main at a
# fixed path and uses the shared .ritz-cache.  Tests in the group
# run on one xdist worker, one at a time; see conftest.py.
pytestmark = pytest.mark.xdist_group("tree")

RITZ_ROOT = Path(__file__).resolve().parent.parent
BUILD_PY = RITZ_ROOT / "build.py"
BUILD_BIN = RITZ_ROOT / "build" / "main"  # where `build.py run` leaves main.ritz


def _run(tmp_path: Path, source: str) -> subprocess.CompletedProcess:
    src = tmp_path / "main.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [sys.executable, str(BUILD_PY), "run", str(src)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )


def _manifest_of(bin_path: Path) -> Path:
    return bin_path.with_name(bin_path.name + ".manifest.json")


def _binary_report(bin_path: Path) -> str:
    """Say what is at `bin_path`: its sha256, manifest and `main` disassembly.

    AGAST #2251: CI saw test_alias_call_inside_an_expression_arm_is_resolved exit
    7, not 11, and this report showed why: the "tree" group had split, so the
    other test here relinked build/main just before this one ran it. Both tests
    still share that path, so it stays as the first evidence if something else
    ever writes there. It reads the file after the run, so a sha256 that differs
    from the manifest's binary_sha256 means something rewrote the binary. Every
    part is best-effort: a report that raised would replace the exit-code failure
    it is there to explain.
    """
    try:
        digest = hashlib.sha256(bin_path.read_bytes()).hexdigest()
    except OSError as err:
        digest = f"unavailable ({err})"
    try:
        manifest = _manifest_of(bin_path).read_text()
    except (OSError, UnicodeDecodeError) as err:
        manifest = f"unavailable ({err})"
    try:
        objdump = subprocess.run(
            ["objdump", "-d", "--no-show-raw-insn", "--disassemble=main", str(bin_path)],
            capture_output=True, text=True, timeout=60,
        )
        disassembly = objdump.stdout + objdump.stderr
    except (OSError, subprocess.SubprocessError) as err:
        disassembly = f"unavailable ({err})"
    return (
        f"--- {bin_path} (AGAST #2251) ---\n"
        f"sha256: {digest}\n"
        f"manifest: {manifest}\n"
        f"disassembly: {disassembly}\n"
    )


def _assert_exit(
    result: subprocess.CompletedProcess, expected: int, bin_path: Path = BUILD_BIN,
) -> None:
    """Assert the exit code, printing `bin_path`'s report first if it is wrong."""
    if result.returncode != expected:
        print(_binary_report(bin_path))
    assert result.returncode == expected, result.stderr + result.stdout


@pytest.mark.integration
def test_alias_import_with_expression_arms_in_an_imported_module(tmp_path):
    # option.ritz's option_is_some is `Some(_) => 1` / `None => 0`.
    result = _run(tmp_path, (
        "import ritzlib.sys as sys\n"
        "import ritzlib.option\n"
        "\n"
        "fn main() -> i32\n"
        "    let o: Option<i32> = Some(5)\n"
        "    option_is_some<i32>(@o) + 6\n"
    ))
    assert "has no attribute 'stmts'" not in result.stderr + result.stdout
    assert result.returncode == 7, result.stderr + result.stdout


@pytest.mark.integration
def test_alias_call_inside_an_expression_arm_is_resolved(tmp_path):
    # `s::isdigit(c) + 10` is an expression arm calling through the alias: it
    # must be rewritten to `isdigit`, not merely left alone.
    result = _run(tmp_path, (
        "import ritzlib.str as s\n"
        "\n"
        "fn main() -> i32\n"
        "    let c: u8 = 55\n"
        "    match c\n"
        "        55 => s::isdigit(c) + 10\n"
        "        _ => 20\n"
    ))
    _assert_exit(result, 11)


# --- Wrong-exit forensics (AGAST #2251) ---------------------------------------


def _completed(returncode: int) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout="the stdout", stderr="the stderr ",
    )


def _fake_binary(tmp_path: Path) -> Path:
    binary = tmp_path / "main"
    binary.write_bytes(b"not really an ELF")
    return binary


@pytest.mark.integration
def test_wrong_exit_reports_the_binary_and_manifest_then_fails(tmp_path, capsys):
    binary = _fake_binary(tmp_path)
    (tmp_path / "main.manifest.json").write_text('{"sources": ["the-manifest-body"]}')
    with pytest.raises(AssertionError) as failure:
        _assert_exit(_completed(7), 11, binary)
    out = capsys.readouterr().out
    assert hashlib.sha256(binary.read_bytes()).hexdigest() in out
    assert "the-manifest-body" in out
    # The failure itself reads as it did before the forensics existed.
    assert "the stderr the stdout" in str(failure.value)


@pytest.mark.unit
def test_right_exit_reports_nothing(tmp_path, capsys):
    _assert_exit(_completed(11), 11, _fake_binary(tmp_path))
    assert capsys.readouterr().out == ""


@pytest.mark.integration
def test_missing_artifacts_do_not_replace_the_exit_failure(tmp_path, capsys):
    # The binary may be gone by the time a failure is reported; the report says
    # so, and the test still fails on the exit code rather than on an OSError.
    with pytest.raises(AssertionError):
        _assert_exit(_completed(7), 11, tmp_path / "absent")
    out = capsys.readouterr().out
    assert "sha256: unavailable" in out
    assert "manifest: unavailable" in out


@pytest.mark.integration
def test_missing_objdump_does_not_replace_the_exit_failure(tmp_path, capsys, monkeypatch):
    binary = _fake_binary(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(AssertionError):
        _assert_exit(_completed(7), 11, binary)
    assert "disassembly: unavailable" in capsys.readouterr().out


@pytest.mark.integration
def test_forensics_read_a_real_build(tmp_path, capsys):
    # Against what `build.py run` really leaves behind, so a moved output path
    # or a renamed `main` symbol shows up here, not during the next CI failure.
    result = _run(tmp_path, "fn main() -> i32\n    11\n")
    assert result.returncode == 11, result.stderr + result.stdout
    with pytest.raises(AssertionError):
        _assert_exit(result, 12)
    out = capsys.readouterr().out
    recorded = json.loads(_manifest_of(BUILD_BIN).read_text())["binary_sha256"]
    assert f"sha256: {recorded}" in out
    assert "<main>:" in out
