"""rld -T SCRIPT against ld.lld -T SCRIPT (../../razm/DESIGN.md "Linker
scripts", "rld tests").

Each link is done by both, and the two executables must agree on the entry,
the PT_LOAD table (virtual and physical address, permissions, file and memory
size), which section each segment holds, and every segment's bytes, with no
masks. The kernel link is the eight kernel `.s` objects plus
`freestanding/kernel.ll` through the real `harland/kernel/linker.ld`.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import pytest

from oracle import (CORPUS, PF_R, PF_W, PF_X, PT_LOAD, PROJECTS, RLLVM_CORPUS,
                    assemble, compile_ll, run, run_tool, tool)

SCRIPTS = CORPUS / "scripts"
KERNEL_SCRIPT = PROJECTS / "harland" / "kernel" / "linker.ld"
# The kernel files, in the order projects/harland/ritz.toml assembles them:
# razm's frozen copies, which its oracle already proves `as` and razm agree on.
KERNEL_S = PROJECTS / "razm" / "tests" / "corpus" / "kernel"
KERNEL_FILES = ["boot", "isr_stubs", "ap_trampoline", "syscall_entry",
                "proc_switch", "user_program", "driver_stub", "smp_user_stub"]
# freestanding_target for harland's kernel (rllvm's `kernel` profile).
KERNEL_FLAGS = ["-c", "-ffreestanding", "-fno-builtin", "-march=native", "-msha",
                "--target=x86_64-none-elf", "-mcmodel=kernel", "-mno-red-zone"]
# The `large` profile: the code-model = "large" bins, linked with user/linker.ld.
LARGE_FLAGS = ["-c", "-ffreestanding", "-fno-builtin", "-march=native", "-msha",
               "--target=x86_64-unknown-none", "-mcmodel=large"]
# The Harland runtime shim (rllvm's `shim` profile is `-c` alone).
SHIM_FLAGS = ["-c"]
# The scripts the tree links with, besides the kernel's (DESIGN "Linker scripts").
TREE_SCRIPTS = {
    "indium-linker_pie": PROJECTS / "indium" / "user" / "linker_pie.ld",
    "prism-linker_pie": PROJECTS / "prism" / "linker_pie.ld",
    "indium-linker": PROJECTS / "indium" / "user" / "linker.ld",
    "indium-user": PROJECTS / "indium" / "user" / "user.ld",
    "indium-linker_spawned": PROJECTS / "indium" / "user" / "linker_spawned.ld",
}
MULTIBOOT2_MAGIC = struct.pack("<I", 0xE85250D6)
MULTIBOOT_SEARCH = 32 * 1024
SHT_NOBITS = 8
SHF_ALLOC = 2


@dataclass(frozen=True)
class Section:
    name: str
    stype: int
    flags: int
    addr: int
    offset: int
    size: int


@dataclass(frozen=True)
class Load:
    flags: int
    offset: int
    vaddr: int
    paddr: int
    filesz: int
    memsz: int
    align: int


@dataclass(frozen=True)
class Elf:
    data: bytes
    entry: int
    loads: list[Load]
    sections: list[Section]
    symbols: dict[str, int]     # every named symbol: its value


def read_elf(path: Path) -> Elf:
    data = path.read_bytes()
    assert data[:4] == b"\x7fELF", f"{path}: not ELF"
    entry, phoff, shoff = struct.unpack_from("<QQQ", data, 24)
    phentsize, phnum, shentsize, shnum, shstrndx = struct.unpack_from("<HHHHH", data, 54)
    loads = []
    for i in range(phnum):
        ptype, *rest = struct.unpack_from("<IIQQQQQQ", data, phoff + i * phentsize)
        if ptype == PT_LOAD:
            loads.append(Load(*rest))
    headers = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * shentsize)
               for i in range(shnum)]

    def name_at(table: int, at: int) -> str:
        off = headers[table][4] + at
        return data[off:data.index(b"\0", off)].decode()

    sections = [Section(name_at(shstrndx, h[0]), h[1], h[2], h[3], h[4], h[5])
                for h in headers[1:]]
    symbols = {}
    for h in headers:
        if h[1] != 2:   # SHT_SYMTAB
            continue
        for i in range(1, h[5] // 24):
            name, _, _, _, value, _ = struct.unpack_from("<IBBHQQ", data, h[4] + i * 24)
            if name:
                symbols[name_at(h[6], name)] = value
    return Elf(data, entry, loads, sections, symbols)


def load_table(e: Elf) -> list[tuple]:
    return [(p.vaddr, p.paddr, p.flags, p.filesz, p.memsz) for p in e.loads]


def segment_map(e: Elf) -> list[list[str]]:
    """Per PT_LOAD, the allocated sections with bytes or memory inside it."""
    out = []
    for p in e.loads:
        out.append([s.name for s in e.sections
                    if s.flags & SHF_ALLOC and s.size > 0
                    and p.vaddr <= s.addr and s.addr + s.size <= p.vaddr + p.memsz])
    return out


def segment_bytes(e: Elf) -> list[bytes]:
    return [e.data[p.offset:p.offset + p.filesz] for p in e.loads]


def assert_same_image(want: Elf, got: Elf) -> None:
    assert got.entry == want.entry, f"entry {got.entry:#x} vs {want.entry:#x}"
    assert load_table(got) == load_table(want)
    assert segment_map(got) == segment_map(want)
    for i, (a, b) in enumerate(zip(segment_bytes(want), segment_bytes(got))):
        assert a == b, f"PT_LOAD {i}: bytes differ"
    for p in got.loads:
        assert p.align == 0x1000 and p.offset % 0x1000 == p.vaddr % 0x1000
    # The allocated sections, the empty ones ld.lld keeps among them.
    assert alloc_table(got) == alloc_table(want)


def alloc_table(e: Elf) -> list[tuple]:
    return [(s.name, s.stype, s.flags, s.addr, s.size)
            for s in e.sections if s.flags & SHF_ALLOC]


@pytest.fixture(scope="module")
def rld() -> Path:
    path = tool("RLD", "rld", "rld")
    if path is None:
        pytest.fail("rld is not built: run ./rz build rld first")
    return path


def link_both(rld: Path, script: Path, objs: list[Path], tmp: Path):
    want, got = tmp / "lld.out", tmp / "rld.out"
    r = run_tool(["ld.lld", "-T", script, "-o", want, *objs])
    assert r.returncode == 0, f"ld.lld: {r.stderr}"
    r = run_tool([rld, "-T", script, "-o", got, *objs])
    assert r.returncode == 0, f"rld: exit {r.returncode}: {r.stderr}"
    return read_elf(want), read_elf(got), r


def assembler(name: str) -> Path | str:
    if name == "as":
        return "as"
    path = tool("RAZM", "razm", "razm")
    if path is None:
        pytest.xfail("razm is not built: run ./rz build razm")
    return path


def kernel_objects(producer: str, tmp: Path) -> list[Path]:
    asm = assembler(producer)
    objs = [assemble(asm, KERNEL_S / f"{f}.s", tmp / f"{f}.o") for f in KERNEL_FILES]
    objs.append(compile_ll("clang", RLLVM_CORPUS / "freestanding" / "kernel.ll",
                           KERNEL_FLAGS, tmp / "kernel.o"))
    objs.append(assemble("as", CORPUS / "kernel_stubs.s", tmp / "stubs.o"))
    return objs


@pytest.mark.parametrize("producer", ["as", "razm"])
def test_kernel_links_like_lld(rld, tmp_path, producer):
    want, got, r = link_both(rld, KERNEL_SCRIPT, kernel_objects(producer, tmp_path), tmp_path)
    assert r.stdout == "" and r.stderr == "", "the kernel script leaves no orphan"
    assert_same_image(want, got)
    # The boot sections run where they load; the kernel's load below its VMA.
    assert [p.vaddr == p.paddr for p in got.loads] == [p.vaddr == p.paddr for p in want.loads]
    at = got.data.find(MULTIBOOT2_MAGIC, 0, MULTIBOOT_SEARCH)
    assert at >= 0 and at % 8 == 0, "Multiboot2 header in the first 32 KiB, 8-aligned"
    assert at == want.data.find(MULTIBOOT2_MAGIC, 0, MULTIBOOT_SEARCH)
    # Every symbol the script assigns or provides has ld.lld's value.
    script_syms = {n for n in want.symbols if n.startswith("__") and n not in
                   ("__ritz_overflow_trap", "__ritz_sret_copy", "__ritz_sret_zero",
                    "__stack_chk_fail", "__stack_chk_guard")}
    assert script_syms, "ld.lld wrote the script's symbols"
    assert {n: got.symbols.get(n) for n in script_syms} == {n: want.symbols[n] for n in script_syms}


def program(tmp: Path) -> list[Path]:
    return [assemble("as", SCRIPTS / "program.s", tmp / "program.o")]


def program_and_provide(tmp: Path) -> list[Path]:
    return program(tmp) + [assemble("as", SCRIPTS / "provide.s", tmp / "provide.o")]


@pytest.mark.parametrize("name", list(TREE_SCRIPTS))
def test_tree_scripts_link_like_lld(rld, tmp_path, name):
    want, got, r = link_both(rld, TREE_SCRIPTS[name], program(tmp_path), tmp_path)
    assert_same_image(want, got)
    assert r.stderr == ""
    # .mydata is matched by no pattern in any of them: one line for it.
    orphans = [line for line in r.stdout.splitlines() if "orphan" in line]
    assert len(orphans) == 1 and ".mydata" in orphans[0], r.stdout


def test_at_offset_carries_forward(rld, tmp_path):
    want, got, _ = link_both(rld, SCRIPTS / "carry.ld", program_and_provide(tmp_path), tmp_path)
    assert_same_image(want, got)
    # .rodata loads at 0x9000; .data and .bss keep its VMA-to-LMA offset.
    rodata, data = got.loads[1], got.loads[2]
    assert rodata.paddr == 0x9000
    assert data.vaddr - data.paddr == rodata.vaddr - rodata.paddr
    assert data.memsz > data.filesz, "the NOLOAD sections add memory, not file bytes"
    assert next(s for s in got.sections if s.name == ".noload").stype == SHT_NOBITS


def test_provide_defines_only_what_is_referenced(rld, tmp_path):
    want, got, _ = link_both(rld, SCRIPTS / "carry.ld", program_and_provide(tmp_path), tmp_path)
    assert got.symbols["__provided_used"] == want.symbols["__provided_used"] == 0x1234
    assert "__provided_unused" not in got.symbols
    assert "__provided_unused" not in want.symbols


def test_orphan_rank_tie_takes_the_later_anchor(rld, tmp_path):
    objs = [assemble("as", SCRIPTS / "tie.s", tmp_path / "tie.o")]
    want, got, _ = link_both(rld, SCRIPTS / "tie.ld", objs, tmp_path)
    assert_same_image(want, got)
    assert [s.name for s in got.sections if s.flags & SHF_ALLOC][-1] == ".ldata"


def test_got_entry_goes_where_the_script_puts_got(rld, tmp_path):
    objs = [assemble("as", CORPUS / "got.s", tmp_path / "got.o"),
            assemble("as", CORPUS / "got_norelax.s", tmp_path / "norelax.o",
                     ["-mrelax-relocations=no"])]
    for script in ("indium-linker_pie", "indium-linker"):
        want, got, _ = link_both(rld, TREE_SCRIPTS[script], objs, tmp_path)
        assert_same_image(want, got)
        assert [s.name for s in got.sections if s.name == ".got"] == [".got"]
        if script == "indium-linker":
            assert run(tmp_path / "rld.out") == run(tmp_path / "lld.out")


def test_large_model_bin_places_like_lld(rld, tmp_path):
    """freestanding/large.ll after the Harland shim, through user/linker.ld:
    .ltext, .lrodata and .ldata are orphans, placed as ld.lld ranks them, and
    the segments hold the same sections. ld.lld rewrites .eh_frame (merged
    CIEs, a zero terminator), which moves what follows it, so addresses and
    bytes are not compared."""
    objs = [compile_ll("clang", RLLVM_CORPUS / "freestanding" / "harland_start.ll",
                       SHIM_FLAGS, tmp_path / "shim.o"),
            compile_ll("clang", RLLVM_CORPUS / "freestanding" / "large.ll",
                       LARGE_FLAGS, tmp_path / "large.o"),
            assemble("as", RLLVM_CORPUS / "extra" / "freestanding.s", tmp_path / "extra.o")]
    want, got, r = link_both(rld, TREE_SCRIPTS["indium-linker"], objs, tmp_path)

    def alloc(e: Elf) -> list[str]:
        return [s.name for s in e.sections if s.flags & SHF_ALLOC]
    assert alloc(got) == alloc(want)
    assert [p.flags for p in got.loads] == [p.flags for p in want.loads] == [
        PF_R | PF_X, PF_R, PF_R | PF_W]
    assert segment_map(got) == segment_map(want)
    assert got.entry == want.entry
    assert len([line for line in r.stdout.splitlines() if "orphan" in line]) == 5


@pytest.mark.parametrize("text, message", [
    ("SECTIONS { .text : { *(.text) } } INCLUDE x.ld", "line 1: unsupported command INCLUDE"),
    ("SECTIONS {\n  .text : { foo.o(.text) }\n}", "line 2: an input pattern's file part must be *"),
    ("SECTIONS { . = 4 * 2; }", "line 1: expected ;"),
    ("SECTIONS { .text : { *(.text) } }\nSECTIONS { }", "line 2: a second SECTIONS"),
    ("ENTRY(_start", "line 1: expected )"),
    ("SECTIONS { .text : { *(.text) } ", "line 1: expected }"),
    ("/* never closed", "line 1: unterminated comment"),
])
def test_script_errors_exit_1(rld, tmp_path, text, message):
    script = tmp_path / "bad.ld"
    script.write_text(text)
    r = run_tool([rld, "-T", script, "-o", tmp_path / "out", *program(tmp_path)])
    assert r.returncode == 1, r
    assert message in r.stderr
    assert not (tmp_path / "out").exists()


def test_missing_script_exits_1(rld, tmp_path):
    r = run_tool([rld, "-T", tmp_path / "none.ld", "-o", tmp_path / "out", *program(tmp_path)])
    assert r.returncode == 1
    assert "none.ld: cannot read file" in r.stderr


def test_T_needs_a_path(rld):
    r = run_tool([rld, "-T"])
    assert r.returncode == 1 and "-T needs a path" in r.stderr
