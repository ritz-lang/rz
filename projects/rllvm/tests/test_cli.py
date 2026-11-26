"""rllvm's argv contract, triples and exit codes (DESIGN.md "What rllvm
replaces", "Triples", "Routing unsupported input").

Exit 0 is an object, 2 is input outside the subset (stderr names the file,
line and construct; the pipeline then uses clang), 1 is any other failure.
Lowering does not exist yet, so a file that parses ends at exit 2 with
"lowering is not implemented".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import run

BODY = "define i32 @f() {\nentry:\n  ret i32 0\n}\n"
NOT_LOWERED = "unsupported: lowering is not implemented"
ELF_TRIPLES = ["x86_64-unknown-linux-gnu", "x86_64-pc-linux-gnu",
               "x86_64-none-elf", "x86_64-unknown-none"]
FOREIGN_TRIPLES = ["x86_64-unknown-windows-gnu", "x86_64-unknown-uefi",
                   "x86_64-pc-windows-msvc", "aarch64-unknown-linux-gnu"]


def module(tmp_path: Path, text: str, name: str = "m.ll") -> Path:
    p = tmp_path / name
    p.write_text(text)
    return p


def rllvm(rllvm_bin, *argv, cwd=None):
    return run([rllvm_bin, *map(str, argv)], cwd=cwd)


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_usage_to_stdout_and_exits_0(rllvm_bin, flag):
    p = rllvm(rllvm_bin, flag)
    assert p.returncode == 0, p
    assert "Usage: rllvm -c" in p.stdout
    assert p.stderr == ""


@pytest.mark.parametrize("argv, message", [
    ([], "-c is required"),
    (["m.ll"], "-c is required"),
    (["-c"], "no input file"),
    (["-c", "m.ll", "-o"], "-o needs a path"),
    (["-c", "m.ll", "m.ll"], "more than one input file"),
    (["-c", "-fno-pic", "m.ll"], "unknown option '-fno-pic'"),
    (["-c", "-mcmodel=medium", "m.ll"], "unknown code model 'medium'"),
    (["-c", "-O4", "m.ll"], "unknown option '-O4'"),
    (["-c", "-S", "m.ll"], "unknown option '-S'"),
    (["-c", "-mcmodel=large", "-fPIC", "m.ll"], "-mcmodel=large with -fPIC"),
    (["-c", "-fPIC", "-mcmodel=large", "m.ll"], "-mcmodel=large with -fPIC"),
    (["-c", "no/such.ll"], "no/such.ll: cannot read file"),
])
def test_cli_errors_exit_1(rllvm_bin, tmp_path, argv, message):
    module(tmp_path, BODY)
    p = rllvm(rllvm_bin, *argv, cwd=tmp_path)
    assert p.returncode == 1, p
    assert message in p.stderr


def test_every_accepted_flag_reaches_lowering(rllvm_bin, tmp_path):
    # Accepted-and-ignored flags change nothing; the file still parses.
    m = module(tmp_path, BODY)
    flags = ["-c", "-fPIC", "-mcmodel=small", "-O0", "-O1", "-O2", "-O3",
             "-Os", "-Oz", "-ffreestanding", "-fno-builtin", "-mno-red-zone",
             "-march=native", "-msha", "-maes", "-mpclmul", "-g"]
    p = rllvm(rllvm_bin, *flags, m, "-o", tmp_path / "m.o")
    assert p.returncode == 2, p
    assert f"{m}: {NOT_LOWERED}" in p.stderr


@pytest.mark.parametrize("model", ["small", "kernel", "large"])
def test_code_models_without_fpic(rllvm_bin, tmp_path, model):
    m = module(tmp_path, BODY)
    p = rllvm(rllvm_bin, "-c", f"-mcmodel={model}", m)
    assert p.returncode == 2, p
    assert NOT_LOWERED in p.stderr


@pytest.mark.parametrize("triple", ELF_TRIPLES)
def test_elf_target_flag_is_accepted(rllvm_bin, tmp_path, triple):
    m = module(tmp_path, BODY)
    p = rllvm(rllvm_bin, "-c", f"--target={triple}", m)
    assert p.returncode == 2 and NOT_LOWERED in p.stderr, p


@pytest.mark.parametrize("triple", ELF_TRIPLES)
def test_elf_module_triple_is_accepted(rllvm_bin, tmp_path, triple):
    m = module(tmp_path, f'target triple = "{triple}"\n' + BODY)
    p = rllvm(rllvm_bin, "-c", m)
    assert p.returncode == 2 and NOT_LOWERED in p.stderr, p


@pytest.mark.parametrize("triple", FOREIGN_TRIPLES)
def test_foreign_target_flag_exits_2(rllvm_bin, tmp_path, triple):
    m = module(tmp_path, BODY)
    p = rllvm(rllvm_bin, "-c", f"--target={triple}", m)
    assert p.returncode == 2, p
    assert f"{m}: unsupported: target triple '{triple}'" in p.stderr


@pytest.mark.parametrize("triple", FOREIGN_TRIPLES)
def test_foreign_module_triple_exits_2_naming_the_line(rllvm_bin, tmp_path, triple):
    m = module(tmp_path, f'; first\ntarget triple = "{triple}"\n' + BODY)
    p = rllvm(rllvm_bin, "-c", m)
    assert p.returncode == 2, p
    assert f"{m}:2: unsupported: target triple '{triple}'" in p.stderr


def test_target_flag_overrides_the_module_triple(rllvm_bin, tmp_path):
    m = module(tmp_path, 'target triple = "x86_64-unknown-windows-gnu"\n' + BODY)
    p = rllvm(rllvm_bin, "-c", "--target=x86_64-none-elf", m)
    assert p.returncode == 2 and NOT_LOWERED in p.stderr, p


def test_no_triple_defaults_to_linux(rllvm_bin, tmp_path):
    p = rllvm(rllvm_bin, "-c", module(tmp_path, BODY))
    assert p.returncode == 2 and NOT_LOWERED in p.stderr, p


def test_empty_datalayout_is_accepted(rllvm_bin, tmp_path):
    p = rllvm(rllvm_bin, "-c", module(tmp_path, 'target datalayout = ""\n' + BODY))
    assert p.returncode == 2 and NOT_LOWERED in p.stderr, p


def test_any_other_datalayout_exits_2(rllvm_bin, tmp_path):
    m = module(tmp_path, 'target datalayout = "e-m:e-i64:64"\n' + BODY)
    p = rllvm(rllvm_bin, "-c", m)
    assert p.returncode == 2, p
    assert f"{m}:1: unsupported: target datalayout 'e-m:e-i64:64'" in p.stderr
