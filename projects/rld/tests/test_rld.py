"""rld against ld.lld (../../razm/DESIGN.md "rld tests").

Each program is linked by both in the no-script `rzrz` shape and run; stdout
and exit status must match. rld exits 1 on any link failure, and stderr
names the cause.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from oracle import (CORPUS, PF_R, PF_W, PF_X, PT_LOAD, RLLVM_CORPUS, RZRZ_FLAGS,
                    SHIM_FLAGS, assemble, compile_ll, link_lld, link_rld,
                    mnemonics, read_executable, run, run_tool, tool)

PKG = Path(__file__).resolve().parent.parent
BASE = 0x200000
PAGE = 0x1000

# The rllvm corpus programs that run, each linked with the shim and the
# hosted helper object: the `.ll` files of one program, and the definitions
# nm must show once.
PROGRAMS = {
    "hello": (["hello"], []),
    "intrin_run": (["intrin_run"], []),
    "asm_run": (["asm_run"], []),
    "abi": (["abi_a", "abi_b"], []),
    "comdat": (["comdat_a", "comdat_b"], ["future_poll"]),
    "weak_strong": (["weak_strong"], ["ritz_platform_fatal"]),
}
# Who compiles each program's .ll files, the shim and the helper object:
# clang and `as`, or rllvm and razm, or for comdat one of each.
PRODUCERS = ["clang", "rllvm"]


@pytest.fixture(scope="module")
def rld() -> Path:
    """The rld under test: $RLD, else this package's debug build."""
    path = tool("RLD", "rld", "rld")
    if path is None:
        pytest.fail("rld is not built: run ./rz build rld first")
    return path


def ritz_tool(env: str, pkg: str, name: str) -> Path:
    path = tool(env, pkg, name)
    if path is None:
        pytest.xfail(f"{name} is not built: run ./rz build {pkg} for this producer")
    return path


def build_objects(producers: list[str], lls: list[str], tmp: Path) -> list[Path]:
    """The shim, the program's objects and the helper object, in link order.
    producers[i] compiles lls[i]; producers[0] builds the shim and helper."""
    first = producers[0]
    if first == "clang":
        shim = compile_ll("clang", RLLVM_CORPUS / "hosted" / "shim.ll", SHIM_FLAGS, tmp / "shim.o")
        extra = assemble("as", RLLVM_CORPUS / "extra" / "hosted.s", tmp / "extra.o")
    else:
        rllvm = ritz_tool("RLLVM", "rllvm", "rllvm")
        razm = ritz_tool("RAZM", "razm", "razm")
        shim = compile_ll(rllvm, RLLVM_CORPUS / "hosted" / "shim.ll", SHIM_FLAGS, tmp / "shim.o")
        extra = assemble(razm, RLLVM_CORPUS / "extra" / "hosted.s", tmp / "extra.o")
    objs = [shim]
    for producer, name in zip(producers, lls):
        compiler = "clang" if producer == "clang" else ritz_tool("RLLVM", "rllvm", "rllvm")
        objs.append(compile_ll(compiler, RLLVM_CORPUS / "hosted" / f"{name}.ll",
                               RZRZ_FLAGS, tmp / f"{name}.{producer}.o"))
    return objs + [extra]


def got_size(exe) -> int:
    return exe.sections.get(".got", (0, 0))[1]


def link_both(rld: Path, objs: list[Path], tmp: Path) -> tuple[Path, Path]:
    want, got = tmp / "lld.out", tmp / "rld.out"
    r = link_lld(objs, want)
    assert r.returncode == 0, f"ld.lld: {r.stderr}"
    r = link_rld(rld, objs, got)
    assert r.returncode == 0, f"rld: exit {r.returncode}: {r.stderr}"
    assert r.stderr == ""
    return want, got


def cases() -> list:
    out = [pytest.param(name, [p] * len(PROGRAMS[name][0]), id=f"{name}-{p}")
           for name in PROGRAMS for p in PRODUCERS]
    out.append(pytest.param("comdat", ["clang", "rllvm"], id="comdat-mixed"))
    return out


@pytest.mark.parametrize("name, producers", cases())
def test_runs_like_lld(rld, tmp_path, name, producers):
    lls, once = PROGRAMS[name]
    objs = build_objects(producers, lls, tmp_path)
    want, got = link_both(rld, objs, tmp_path)
    assert run(got) == run(want)
    exe = read_executable(got)
    for sym in once:
        assert len(exe.symbols.get(sym, [])) == 1, f"{sym}: one definition"
    # A GOT load of an in-image symbol relaxes: GOT entries only where
    # ld.lld makes them (it writes an empty .got header where rld writes none).
    assert got_size(exe) == got_size(read_executable(want))


def test_weak_definition_loses_to_strong(rld, tmp_path):
    objs = build_objects(["clang"], ["weak_strong"], tmp_path)
    _, got = link_both(rld, objs, tmp_path)
    assert run(got).status == 7


def test_layout_is_the_no_script_executable(rld, tmp_path):
    objs = build_objects(["clang"], ["hello"], tmp_path)
    _, got = link_both(rld, objs, tmp_path)
    exe = read_executable(got)
    assert exe.etype == 2, "ET_EXEC"
    assert exe.symbols["_start"] == [exe.entry]
    loads = [s for s in exe.segments if s.ptype == PT_LOAD]
    assert [s.flags for s in loads] == [PF_R, PF_R | PF_X, PF_R | PF_W]
    assert loads[0].offset == 0 and loads[0].vaddr == BASE
    for s in loads:
        assert s.vaddr % PAGE == 0 and s.vaddr == BASE + s.offset
        assert s.paddr == s.vaddr and s.align == PAGE
        assert s.memsz >= s.filesz
    for a, b in zip(loads, loads[1:]):
        assert b.vaddr >= a.vaddr + a.memsz, "each segment on a new page"
    # Every allocated input section keeps its own name.
    assert {".rodata", ".text", ".data", ".bss", ".eh_frame"} <= set(exe.sections)


def test_got_loads_relax_like_lld(rld, tmp_path):
    objs = [assemble("as", CORPUS / "got.s", tmp_path / "got.o"),
            assemble("as", CORPUS / "got_norelax.s", tmp_path / "norelax.o",
                     ["-mrelax-relocations=no"])]
    want, got = link_both(rld, objs, tmp_path)
    result = run(got)
    assert result.status == 0, f"check {result.status} failed"
    assert result == run(want)
    assert mnemonics(got) == mnemonics(want)
    # One entry, for the plain GOTPCREL and the loads that keep it.
    assert got_size(read_executable(got)) == got_size(read_executable(want)) == 8


def test_out_of_range_got_load_keeps_its_entry(rld, tmp_path):
    objs = [assemble("as", CORPUS / "got_far.s", tmp_path / "far.o")]
    want, got = link_both(rld, objs, tmp_path)
    assert run(got).status == 0
    assert run(want).status == 0
    assert got_size(read_executable(got)) == got_size(read_executable(want)) == 8


@pytest.mark.parametrize("sources, message", [
    (["undefined.s"], "undefined symbol: missing"),
    (["dup.s", "dup.s"], "duplicate symbol: _start"),
    (["common.s"], "common symbol shared"),
    (["no_start.s"], "entry symbol _start is not defined"),
])
def test_link_errors_exit_1(rld, tmp_path, sources, message):
    objs = [assemble("as", CORPUS / s, tmp_path / f"{i}.o") for i, s in enumerate(sources)]
    r = link_rld(rld, objs, tmp_path / "out")
    assert r.returncode == 1, r
    assert message in r.stderr
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("argv, message", [
    ([], "no input files"),
    (["-o"], "-o needs a path"),
    (["--pie", "x.o"], "unknown option"),
    (["no/such/file.o"], "no/such/file.o: cannot read file"),
    (["undefined.s"], "undefined.s: not an ELF file"),
])
def test_cli_errors_exit_1(rld, argv, message):
    r = run_tool([rld, *argv], cwd=CORPUS)
    assert r.returncode == 1, r
    assert message in r.stderr


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_exits_0(rld, flag):
    r = run_tool([rld, flag])
    assert r.returncode == 0
    assert "Usage: rld" in r.stdout
