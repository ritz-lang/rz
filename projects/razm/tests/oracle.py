"""razm's oracle driver: compare a relocatable ELF64 object with `as --64`'s.

DESIGN.md "What razm checks" is the contract. For one `.s` file the two
objects must agree on

- every section other than the symbol, string and relocation tables: name,
  type, flags, alignment, size and bytes;
- every relocation, per section: offset, type and addend, with the target
  normalized (a global or undefined symbol by name, a local one as
  (section, offset), the addend folded into the offset);
- every symbol either tool writes, other than section and file symbols:
  name, section, value, size, type and binding;

and the kernel files' `ld.lld -T kernel/linker.ld` links must be
byte-identical. Whole `.o` files are not compared: symbol order and string
table layout are not part of the contract.

The driver shells out to `as` and `ld.lld` and reads ELF itself. It does not
import build_pipeline.py.
"""

from __future__ import annotations

import struct
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

CORPUS = Path(__file__).resolve().parent / "corpus"

# The kernel files, in the order projects/harland/ritz.toml assembles them
# (link order decides the linked bytes).
KERNEL_FILES = [
    "kernel/boot.s",
    "kernel/isr_stubs.s",
    "kernel/ap_trampoline.s",
    "kernel/syscall_entry.s",
    "kernel/proc_switch.s",
    "kernel/user_program.s",
    "kernel/driver_stub.s",
    "kernel/smp_user_stub.s",
]
CORPUS_FILES = KERNEL_FILES + ["boot/uefi_entry.s", "synthetic/incbin.s"]
KERNEL_LINKER_SCRIPT = "kernel/linker.ld"

TOOL_TIMEOUT = 60  # seconds, per as / razm / ld.lld run

ET_REL = 1
EM_X86_64 = 62
ELFCLASS64 = 2
ELFDATA2LSB = 1

SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_RELA = 4
SHT_NOBITS = 8
SHT_REL = 9
# Tables whose layout is not in the contract; their content is compared
# through symbols and relocations instead.
TABLE_TYPES = {SHT_SYMTAB, SHT_STRTAB, SHT_RELA, SHT_REL}

SHN_UNDEF = 0
SHN_ABS = 0xFFF1
SHN_COMMON = 0xFFF2

STB_LOCAL = 0
STT_SECTION = 3
STT_FILE = 4

RELOC_NAMES = {
    0: "R_X86_64_NONE", 1: "R_X86_64_64", 2: "R_X86_64_PC32",
    4: "R_X86_64_PLT32", 9: "R_X86_64_GOTPCREL", 10: "R_X86_64_32",
    11: "R_X86_64_32S", 12: "R_X86_64_16", 13: "R_X86_64_PC16",
    14: "R_X86_64_8", 15: "R_X86_64_PC8", 41: "R_X86_64_GOTPCRELX",
    42: "R_X86_64_REX_GOTPCRELX",
}


class ElfError(Exception):
    """The bytes are not an ELF64 x86-64 object this reader understands."""


@dataclass
class Section:
    index: int
    name: str
    type: int
    flags: int
    align: int
    size: int
    data: bytes            # b"" for SHT_NOBITS
    link: int
    info: int
    header_off: int        # file offset of this section header
    data_off: int          # sh_offset


@dataclass
class Symbol:
    name: str
    section: str           # section name, "*UND*", "*ABS*" or "*COMMON*"
    value: int
    size: int
    type: int
    binding: int
    file_off: int          # file offset of this Elf64_Sym


@dataclass
class Reloc:
    section: str           # the section the relocation applies to
    offset: int
    type: int
    symbol: Symbol
    addend: int
    file_off: int          # file offset of this Elf64_Rela


@dataclass
class ElfObject:
    e_type: int
    e_machine: int
    sections: list[Section] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    relocs: list[Reloc] = field(default_factory=list)


def _cstr(table: bytes, off: int) -> str:
    end = table.find(b"\0", off)
    if end < 0:
        raise ElfError(f"string at {off} runs off its table")
    return table[off:end].decode("utf-8", "replace")


def read_elf(data: bytes) -> ElfObject:
    """Parse a relocatable ELF64 little-endian object."""
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ElfError("not an ELF file")
    if data[4] != ELFCLASS64 or data[5] != ELFDATA2LSB:
        raise ElfError("not ELF64 little-endian")
    (e_type, e_machine, _ver, _entry, _phoff, shoff, _flags, _ehsize,
     _phentsize, _phnum, shentsize, shnum, shstrndx) = struct.unpack_from(
        "<HHIQQQIHHHHHH", data, 16)
    if shentsize != 64:
        raise ElfError(f"e_shentsize {shentsize}, want 64")
    obj = ElfObject(e_type, e_machine)

    raw = []
    for i in range(shnum):
        hoff = shoff + i * shentsize
        (name, typ, flags, _addr, off, size, link, info, align,
         _entsize) = struct.unpack_from("<IIQQQQIIQQ", data, hoff)
        raw.append((name, typ, flags, off, size, link, info, align, hoff))
    if not raw:
        raise ElfError("no section headers")
    shstr = raw[shstrndx]
    shstrtab = data[shstr[3]:shstr[3] + shstr[4]]
    for i, (name, typ, flags, off, size, link, info, align, hoff) in enumerate(raw):
        body = b"" if typ == SHT_NOBITS else data[off:off + size]
        obj.sections.append(Section(i, _cstr(shstrtab, name), typ, flags,
                                    align, size, body, link, info, hoff, off))

    def sec_name(shndx: int) -> str:
        if shndx == SHN_UNDEF:
            return "*UND*"
        if shndx == SHN_ABS:
            return "*ABS*"
        if shndx == SHN_COMMON:
            return "*COMMON*"
        return obj.sections[shndx].name

    symtabs = [s for s in obj.sections if s.type == SHT_SYMTAB]
    if len(symtabs) > 1:
        raise ElfError("more than one .symtab")
    by_index: list[Symbol] = []
    if symtabs:
        st = symtabs[0]
        strtab = obj.sections[st.link].data
        for i in range(st.size // 24):
            soff = st.data_off + i * 24
            name, info, _other, shndx, value, size = struct.unpack_from(
                "<IBBHQQ", data, soff)
            sym = Symbol(_cstr(strtab, name), sec_name(shndx), value, size,
                         info & 0xF, info >> 4, soff)
            if sym.type == STT_SECTION and not sym.name:
                sym.name = sym.section
            by_index.append(sym)
        obj.symbols = by_index[1:]

    for rs in obj.sections:
        if rs.type == SHT_REL:
            raise ElfError(f"{rs.name}: SHT_REL; an x86-64 object uses RELA")
        if rs.type != SHT_RELA:
            continue
        target = obj.sections[rs.info].name
        for i in range(rs.size // 24):
            roff = rs.data_off + i * 24
            offset, info, addend = struct.unpack_from("<QQq", data, roff)
            obj.relocs.append(Reloc(target, offset, info & 0xFFFFFFFF,
                                    by_index[info >> 32], addend, roff))
    return obj


def reloc_key(r: Reloc) -> tuple:
    """A relocation with its target normalized (DESIGN.md): global or
    undefined by name with the addend, local as (section, offset)."""
    s = r.symbol
    if s.binding == STB_LOCAL and s.section not in ("*UND*", "*ABS*"):
        target = ("local", s.section, s.value + r.addend)
    else:
        target = ("symbol", s.name, r.addend)
    return (r.offset, r.type, target)


def _fmt_reloc(key: tuple) -> str:
    offset, typ, (kind, a, b) = key
    name = RELOC_NAMES.get(typ, str(typ))
    where = f"{a}+{b:#x}" if kind == "local" else f"{a}{b:+#x}"
    return f"{offset:#x} {name} -> {kind} {where}"


def _compared_symbols(obj: ElfObject) -> dict[str, list[Symbol]]:
    out: dict[str, list[Symbol]] = {}
    for s in obj.symbols:
        if s.type in (STT_SECTION, STT_FILE):
            continue
        out.setdefault(s.name, []).append(s)
    return out


def _first_diff(a: bytes, b: bytes) -> int:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def compare_objects(want: ElfObject, got: ElfObject) -> list[str]:
    """Every way `got` differs from `want` under the contract; [] if none."""
    diffs: list[str] = []
    for label, w, g in (("e_type", want.e_type, got.e_type),
                        ("e_machine", want.e_machine, got.e_machine)):
        if w != g:
            diffs.append(f"header: {label} {g}, want {w}")

    def sections(obj: ElfObject, who: str) -> dict[str, Section]:
        out: dict[str, Section] = {}
        for s in obj.sections[1:]:
            if s.type in TABLE_TYPES:
                continue
            if s.name in out:
                diffs.append(f"{who}: section {s.name} appears twice")
            out[s.name] = s
        return out

    ws, gs = sections(want, "oracle"), sections(got, "candidate")
    for name in sorted(ws.keys() - gs.keys()):
        diffs.append(f"section {name}: missing")
    for name in sorted(gs.keys() - ws.keys()):
        diffs.append(f"section {name}: not in the oracle object")
    for name in sorted(ws.keys() & gs.keys()):
        w, g = ws[name], gs[name]
        for label, wv, gv in (("type", w.type, g.type),
                              ("flags", w.flags, g.flags),
                              ("align", w.align, g.align),
                              ("size", w.size, g.size)):
            if wv != gv:
                diffs.append(f"section {name}: {label} {gv:#x}, want {wv:#x}")
        if w.data != g.data:
            at = _first_diff(w.data, g.data)
            diffs.append(f"section {name}: bytes differ from offset {at:#x}")

    wr: dict[str, list[tuple]] = {}
    gr: dict[str, list[tuple]] = {}
    for src, dst in ((want, wr), (got, gr)):
        for r in src.relocs:
            dst.setdefault(r.section, []).append(reloc_key(r))
    for name in sorted(wr.keys() | gr.keys()):
        w = sorted(wr.get(name, []))
        g = sorted(gr.get(name, []))
        for key in [k for k in w if k not in g]:
            diffs.append(f"relocation in {name}: missing {_fmt_reloc(key)}")
        for key in [k for k in g if k not in w]:
            diffs.append(f"relocation in {name}: unexpected {_fmt_reloc(key)}")

    wsym, gsym = _compared_symbols(want), _compared_symbols(got)
    for name in sorted(wsym.keys() - gsym.keys()):
        diffs.append(f"symbol {name}: missing")
    for name in sorted(gsym.keys() - wsym.keys()):
        diffs.append(f"symbol {name}: not in the oracle object")
    for name in sorted(wsym.keys() & gsym.keys()):
        wl, gl = wsym[name], gsym[name]
        if len(wl) != 1 or len(gl) != 1:
            diffs.append(f"symbol {name}: defined {len(gl)} times, "
                         f"{len(wl)} in the oracle; names must be unique")
            continue
        w, g = wl[0], gl[0]
        for label, wv, gv in (("section", w.section, g.section),
                              ("value", w.value, g.value),
                              ("size", w.size, g.size),
                              ("type", w.type, g.type),
                              ("binding", w.binding, g.binding)):
            if wv != gv:
                diffs.append(f"symbol {name}: {label} {gv}, want {wv}")
    return diffs


@dataclass
class ToolResult:
    returncode: int
    stderr: str


def _run(argv: list[str], cwd: Path) -> ToolResult:
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                       timeout=TOOL_TIMEOUT)
    return ToolResult(p.returncode, p.stderr)


def assemble(argv0: list[str], rel: str, out: Path,
             root: Path = CORPUS) -> ToolResult:
    """Run `<argv0> --64 -o OUT REL` from `root`, as assemble_objects runs
    `as` from the package directory, so `.incbin` paths resolve."""
    return _run([*argv0, "--64", "-o", str(out), rel], root)


def assemble_with_as(rel: str, out: Path, root: Path = CORPUS) -> None:
    r = assemble(["as"], rel, out, root)
    if r.returncode != 0:
        raise RuntimeError(f"as --64 {rel} failed ({r.returncode}): {r.stderr}")


def link_kernel(objects: list[Path], out: Path, root: Path = CORPUS) -> None:
    """The kernel link DESIGN.md names, from `root` so the script resolves."""
    argv = ["ld.lld", "-T", KERNEL_LINKER_SCRIPT,
            "--unresolved-symbols=ignore-all", "--strip-all",
            "-o", str(out), *map(str, objects)]
    r = _run(argv, root)
    if r.returncode != 0:
        raise RuntimeError(f"ld.lld failed ({r.returncode}): {r.stderr}")


def compare_files(want: Path, got: Path) -> list[str]:
    return compare_objects(read_elf(want.read_bytes()), read_elf(got.read_bytes()))


def compare_links(want: Path, got: Path) -> list[str]:
    a, b = want.read_bytes(), got.read_bytes()
    if a == b:
        return []
    return [f"linked kernel: {got.name} differs from {want.name} at byte "
            f"{_first_diff(a, b):#x} (sizes {len(b)} vs {len(a)})"]
