"""rld against ld.lld and clang (../../razm/DESIGN.md "rld tests").

Each program is linked by both in the no-script `rzrz` shape and run; stdout
and exit status must match. The hosted runs link with `clang -nostdlib` and
with `rld --hosted`, and match the same way. The freestanding PIE, which no
loader on this host relocates, is compared with ld.lld's on its dynamic tags
and its load-time relocations. rld exits 1 on any link failure, and stderr
names the cause.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from oracle import (CORPUS, DF_1_PIE, DT_FLAGS_1, DT_NEEDED, ET_DYN, PF_R,
                    PF_W, PF_X, PT_DYNAMIC, PT_INTERP, PT_LOAD, PT_PHDR,
                    R_X86_64_RELATIVE, RLLVM_CORPUS, RZRZ_FLAGS, SHIM_FLAGS,
                    assemble, compile_ll, link_clang_hosted, link_lld,
                    link_lld_pie, link_rld, mnemonics, read_dynamic,
                    read_executable, run, run_tool, tool)

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


def build_objects(producers: list[str], lls: list[str], tmp: Path,
                  flags: list[str] = RZRZ_FLAGS) -> list[Path]:
    """The shim, the program's objects and the helper object, in link order.
    producers[i] compiles lls[i] with `flags`; producers[0] builds the shim
    and helper."""
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
                               flags, tmp / f"{name}.{producer}.o"))
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
    (["--pie", "x.o"], "--pie needs --no-dynamic-linker"),
    (["--no-dynamic-linker", "x.o"], "--no-dynamic-linker needs --pie"),
    (["--hosted", "--pie", "--no-dynamic-linker", "x.o"], "--hosted takes no --pie"),
    (["--hosted", "-T", "x.ld", "x.o"], "--hosted takes no -T"),
    (["-T"], "-T needs a path"),
    (["--frob", "x.o"], "unknown option"),
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


# --- PIEs (DESIGN.md "Outputs": the hosted and freestanding PIE rows) ---

# The hosted .ll flags (link_hosted's objects): -fPIC, so every external
# data reference is a GOT load, which a PIE relaxes only to a lea.
HOSTED_FLAGS = ["-c", "-O2", "-fPIC", "-ffreestanding", "-fno-builtin"]
# A pic bin's .ll flags (freestanding_target with pic).
PIC_FLAGS = ["-c", "-ffreestanding", "-fno-builtin", "-march=native", "-msha",
             "--target=x86_64-unknown-none", "-fPIC"]
INTERP = "/lib64/ld-linux-x86-64.so.2"
PIE = ["--pie", "--no-dynamic-linker"]

DT_HASH, DT_STRTAB, DT_SYMTAB, DT_RELACOUNT = 4, 5, 6, 0x6ffffff9
DT_STRSZ, DT_SYMENT, DT_DEBUG, DT_GNU_HASH = 10, 11, 21, 0x6ffffef5
# The tags both PIEs carry; RELA* only when there are relocations, HASH
# only in the freestanding PIE (the hosted link is --hash-style=gnu).
BASE_TAGS = {DT_FLAGS_1, DT_DEBUG, DT_SYMTAB, DT_SYMENT, DT_STRTAB, DT_STRSZ,
             DT_GNU_HASH}
RELA_TAGS = {7, 8, 9, DT_RELACOUNT}


def link_hosted_both(rld: Path, objs: list[Path], tmp: Path) -> tuple[Path, Path]:
    want, got = tmp / "clang.out", tmp / "rld.out"
    r = link_clang_hosted(objs, want)
    assert r.returncode == 0, f"clang: {r.stderr}"
    r = link_rld(rld, objs, got, ["--hosted"])
    assert r.returncode == 0, f"rld: exit {r.returncode}: {r.stderr}"
    assert r.stderr == ""
    return want, got


def hosted_cases() -> list:
    return [pytest.param(name, [p] * len(PROGRAMS[name][0]), id=f"{name}-{p}")
            for name in PROGRAMS for p in PRODUCERS]


@pytest.mark.parametrize("name, producers", hosted_cases())
def test_hosted_runs_like_clang(rld, tmp_path, name, producers):
    lls, once = PROGRAMS[name]
    objs = build_objects(producers, lls, tmp_path, HOSTED_FLAGS)
    want, got = link_hosted_both(rld, objs, tmp_path)
    assert run(got) == run(want)
    exe = read_executable(got)
    for sym in once:
        assert len(exe.symbols.get(sym, [])) == 1, f"{sym}: one definition"


def assert_pie_shape(path: Path, hosted: bool) -> None:
    exe = read_executable(path)
    dyn = read_dynamic(path)
    assert exe.etype == ET_DYN
    assert dyn.tags[DT_FLAGS_1] & DF_1_PIE
    assert DT_NEEDED not in dyn.tags
    assert dyn.interp == (INTERP if hosted else None)
    assert sum(s.ptype == PT_DYNAMIC for s in exe.segments) == 1
    want = BASE_TAGS | (RELA_TAGS if dyn.relocs else set()) | (set() if hosted else {DT_HASH})
    assert set(dyn.tags) == want
    assert all(t == R_X86_64_RELATIVE for _, t, _ in dyn.relocs), "RELATIVE only"
    if dyn.relocs:
        assert dyn.tags[DT_RELACOUNT] == len(dyn.relocs)
    assert dyn.tags[DT_STRSZ] == 1, "an empty .dynstr"


def test_hosted_layout_is_the_linux_pie(rld, tmp_path):
    objs = build_objects(["clang"], ["hello"], tmp_path, HOSTED_FLAGS)
    _, got = link_hosted_both(rld, objs, tmp_path)
    assert_pie_shape(got, hosted=True)
    exe = read_executable(got)
    assert exe.symbols["_start"] == [exe.entry]
    assert sum(s.ptype == PT_INTERP for s in exe.segments) == 1


def fixture_objects(tmp: Path) -> list[Path]:
    """The initialized-pointer fixture and its absolute symbol."""
    return [assemble("as", CORPUS / "pie.s", tmp / "pie.o"),
            assemble("as", CORPUS / "pie_abs.s", tmp / "pie_abs.o")]


def test_hosted_pie_relocates_pointers_and_got(rld, tmp_path):
    """Run under ld.so at a random base: each pointer must hold its loaded
    address, so each needs its RELATIVE."""
    objs = fixture_objects(tmp_path)
    want, got = link_hosted_both(rld, objs, tmp_path)
    assert run(want).status == 0
    assert run(got).status == 0
    dyn = read_dynamic(got)
    assert len(dyn.relocs) == 3, "tab, tab + 8 and the one GOT entry"
    assert_pie_shape(got, hosted=True)


def located(exe, addr: int) -> tuple[str, int]:
    """`addr` as (output section, offset in it), so two layouts compare."""
    for name, (start, size) in exe.sections.items():
        if start <= addr < start + size and start != 0:
            return name, addr - start
    raise AssertionError(f"{addr:#x} is in no section")


def relocs_by_section(path: Path) -> list:
    exe = read_executable(path)
    return sorted((located(exe, o), t, located(exe, a)) for o, t, a in read_dynamic(path).relocs)


def pic_objects(producer: str, tmp: Path) -> list[Path]:
    """freestanding/pic.ll with the Harland shim first and the freestanding
    helper object, plus the initialized-pointer fixture."""
    fs = RLLVM_CORPUS / "freestanding"
    cc = "clang" if producer == "clang" else ritz_tool("RLLVM", "rllvm", "rllvm")
    return [compile_ll(cc, fs / "harland_start.ll", PIC_FLAGS, tmp / "start.o"),
            compile_ll(cc, fs / "pic.ll", PIC_FLAGS, tmp / "pic.o"),
            assemble("as", RLLVM_CORPUS / "extra" / "freestanding.s", tmp / "extra.o"),
            *fixture_objects(tmp)]


def link_pie_both(rld: Path, objs: list[Path], tmp: Path,
                  script: Path | None = None) -> tuple[Path, Path]:
    want, got = tmp / "lld.out", tmp / "rld.out"
    r = link_lld_pie(objs, want, script)
    assert r.returncode == 0, f"ld.lld: {r.stderr}"
    t = ["-T", script] if script else []
    r = link_rld(rld, objs, got, [*PIE, *t])
    assert r.returncode == 0, f"rld: exit {r.returncode}: {r.stderr}"
    return want, got


@pytest.mark.parametrize("producer", PRODUCERS)
def test_freestanding_pie_relocations_match_lld(rld, tmp_path, producer):
    # pie.s's _start would clash with the shim's: link it on its own too.
    objs = pic_objects(producer, tmp_path)
    for name, group in [("pic", objs[:3]), ("fixture", objs[3:])]:
        d = tmp_path / name
        d.mkdir()
        want, got = link_pie_both(rld, group, d)
        assert_pie_shape(got, hosted=False)
        assert set(read_dynamic(got).tags) == set(read_dynamic(want).tags)
        assert relocs_by_section(got) == relocs_by_section(want)
        assert read_dynamic(got).relocs, f"{name}: pointers in writable data"


PIE_SCRIPT = PKG.parent / "indium" / "user" / "linker_pie.ld"


def load_table(path: Path) -> list:
    return [(s.vaddr, s.paddr, s.flags, s.filesz, s.memsz)
            for s in read_executable(path).segments if s.ptype == PT_LOAD]


def load_bytes(path: Path) -> list[bytes]:
    """Each PT_LOAD's file bytes, with each RELATIVE's word zeroed: ld.lld
    writes 0 there, rld the link-time address (DESIGN.md "Load-time
    relocations")."""
    data = bytearray(path.read_bytes())
    loads = [s for s in read_executable(path).segments if s.ptype == PT_LOAD]
    for offset, _, _ in read_dynamic(path).relocs:
        for s in loads:
            if s.vaddr <= offset < s.vaddr + s.filesz:
                at = s.offset + offset - s.vaddr
                data[at:at + 8] = bytes(8)
    return [bytes(data[s.offset:s.offset + s.filesz]) for s in loads]


@pytest.mark.parametrize("script", [PIE_SCRIPT, CORPUS / "pie_inside.ld"],
                         ids=["linker_pie", "pie_inside"])
@pytest.mark.parametrize("producer", PRODUCERS)
def test_scripted_pie_matches_lld(rld, tmp_path, producer, script):
    """A pic bin's link through user/linker_pie.ld, and through a script
    that puts the GOT and .got.plt inside .data. The script fixes the
    layout, so the PT_LOAD table, every tag's value, each relocation's
    (offset, type, addend) and the loaded bytes must match ld.lld's."""
    objs = pic_objects(producer, tmp_path)
    for name, group in [("pic", objs[:3]), ("fixture", objs[3:])]:
        d = tmp_path / name
        d.mkdir()
        want, got = link_pie_both(rld, group, d, script)
        assert_pie_shape(got, hosted=False)
        assert load_table(got) == load_table(want)
        assert read_dynamic(got).tags == read_dynamic(want).tags
        assert sorted(read_dynamic(got).relocs) == sorted(read_dynamic(want).relocs)
        assert load_bytes(got) == load_bytes(want)
        assert read_dynamic(got).relocs, f"{name}: pointers in writable data"
        assert read_executable(got).entry == read_executable(want).entry
        # The script loads no headers, so as in ld.lld's there is no PT_PHDR.
        assert not any(s.ptype == PT_PHDR for s in read_executable(got).segments)


@pytest.mark.parametrize("pie, script, section", [
    (True, "pie_mismatch.ld", ".dynamic"),
    (False, "rela_mismatch.ld", ".rela.dyn"),
], ids=["pie", "executable"])
def test_section_type_mismatch_exits_1(rld, tmp_path, pie, script, section):
    """A linker-made section of its own type among .data's PROGBITS:
    ld.lld refuses it, and so does rld."""
    objs = fixture_objects(tmp_path)
    flags = [*(PIE if pie else []), "-T", CORPUS / script]
    lld = run_tool(["ld.lld", *flags, "-o", tmp_path / "lld.out", *objs])
    assert f"section type mismatch for {section}" in lld.stderr
    r = link_rld(rld, objs, tmp_path / "out", flags)
    assert r.returncode == 1, r
    assert f"section type mismatch for {section}" in r.stderr
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("source, message", [
    ("textrel.s", "relocation type 1 against x is not position-independent"),
    ("abs32.s", "relocation type 11 against x is not position-independent"),
])
def test_absolute_relocations_a_pie_cannot_load(rld, tmp_path, source, message):
    objs = [assemble("as", CORPUS / source, tmp_path / "in.o")]
    assert link_lld_pie(objs, tmp_path / "lld.out").returncode != 0
    r = link_rld(rld, objs, tmp_path / "out", PIE)
    assert r.returncode == 1, r
    assert message in r.stderr
    # The same object links as the no-script executable.
    assert link_rld(rld, objs, tmp_path / "exe").returncode == 0
