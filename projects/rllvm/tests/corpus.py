"""rllvm's clang-oracle corpus driver (../razm/DESIGN.md "Tests",
"Equivalence bar").

Each entry is a frozen `corpus/<dir>/<name>.ll` and a one-word profile in
`<name>.profile`:

    hosted     -c -O2 -fPIC -ffreestanding -fno-builtin (OBJ_CLANG_FLAGS)
    shim       -c, nothing else (ensure_runtime_object): both runtime shims
    small-pic  freestanding_target for a `pic` bin on x86_64-unknown-none
    kernel     freestanding_target for harland's kernel (x86_64-none-elf)
    large      freestanding_target for `code-model = "large"` bins

Clang and rllvm get the same argv. The links use the existing linkers:
`clang -nostdlib` for hosted entries, `ld.lld` for freestanding ones. The
"one razm object" each link takes is built from `corpus/extra/*.s` with
`as --64` until razm assembles it.

The driver shells out to clang, as, ld.lld, objdump and nm, and reads ELF
relocations itself. It does not import build_pipeline.py.
"""

from __future__ import annotations

import re
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path

CORPUS = Path(__file__).resolve().parent / "corpus"

TOOL_TIMEOUT = 60  # seconds, per compile / link / run

_FREESTANDING = ["-c", "-ffreestanding", "-fno-builtin", "-march=native", "-msha"]
PROFILE_FLAGS = {
    "hosted": ["-c", "-O2", "-fPIC", "-ffreestanding", "-fno-builtin"],
    "shim": ["-c"],
    "small-pic": [*_FREESTANDING, "--target=x86_64-unknown-none", "-fPIC"],
    "kernel": [*_FREESTANDING, "--target=x86_64-none-elf",
               "-mcmodel=kernel", "-mno-red-zone"],
    "large": [*_FREESTANDING, "--target=x86_64-unknown-none",
              "-mcmodel=large"],
}

# The relocation profile (DESIGN "Relocations") each compile profile gets.
# The shims are compiled with no -fPIC: clang 21 defaults to PIE.
RELOC_PROFILE = {
    "hosted": "small-pic",
    "small-pic": "small-pic",
    "shim": "small-pie",
    "kernel": "kernel",
    "large": "large",
}

R_X86_64_64 = 1
R_X86_64_PC32 = 2
R_X86_64_PLT32 = 4
R_X86_64_32 = 10
R_X86_64_32S = 11
R_X86_64_REX_GOTPCRELX = 42
RELOC_NAMES = {
    0: "R_X86_64_NONE", 1: "R_X86_64_64", 2: "R_X86_64_PC32",
    4: "R_X86_64_PLT32", 9: "R_X86_64_GOTPCREL", 10: "R_X86_64_32",
    11: "R_X86_64_32S", 41: "R_X86_64_GOTPCRELX",
    42: "R_X86_64_REX_GOTPCRELX",
}


@dataclass(frozen=True)
class RelocRule:
    external_data: int
    internal_data: int
    calls: frozenset[int]


# DESIGN "Relocations", one row per profile. Inline asm adds PC32 for a
# template's `sym(%rip)` and PLT32 for its `call sym`, in every model.
RELOC_RULES = {
    "small-pic": RelocRule(R_X86_64_REX_GOTPCRELX, R_X86_64_PC32,
                           frozenset({R_X86_64_PLT32})),
    "small-pie": RelocRule(R_X86_64_REX_GOTPCRELX, R_X86_64_PC32,
                           frozenset({R_X86_64_PLT32})),
    "kernel": RelocRule(R_X86_64_REX_GOTPCRELX, R_X86_64_32S,
                        frozenset({R_X86_64_PLT32})),
    "large": RelocRule(R_X86_64_64, R_X86_64_64, frozenset({R_X86_64_64})),
}
ASM_TEMPLATE_RELOCS = frozenset({R_X86_64_PC32, R_X86_64_PLT32})
# sspstrong's guard load: clang 21 addresses __stack_chk_guard PC-relative
# (PC32) under the kernel model too, not through the table's types.
STACK_GUARD = "__stack_chk_guard"

# DESIGN "Inline asm": the mnemonics the blocks and shims contain, and the
# name `objdump -d -M suffix` prints for those it spells differently.
ASM_MNEMONICS = (
    "addq addl andq call clflush cli cpuid decq hlt inb inl invlpg inw jmpq "
    "jnz leaq lfence lidt ltr mfence movb movl movq movw nop nopl outb outl "
    "outw pause popq pushfq rdmsr rdtsc retq sfence shlq sti syscall wrmsr "
    "xgetbv xorl xorq").split()
OBJDUMP_ALIASES = {"call": {"callq"}, "jnz": {"jne"}, "ltr": {"ltrl"}}
SIMD_MNEMONICS = ("sha256rnds2 sha256msg1 sha256msg2 aesenc aesenclast aesdec "
                  "aesdeclast aesimc aeskeygenassist psadbw pclmulqdq").split()
INTRIN_MNEMONICS = ["ud2", "bswap", "andps", "andpd"]
# Calls rllvm never emits: compiler-rt bit counts and libc memory and math.
FORBIDDEN_REFS = ["__clz", "__ctz", "__popcount", "memcpy", "memset",
                  "memmove", "floor", "ceil"]


@dataclass(frozen=True)
class Entry:
    rel: str               # path under corpus/, e.g. "hosted/hello.ll"
    profile: str

    @property
    def path(self) -> Path:
        return CORPUS / self.rel

    @property
    def stem(self) -> str:
        return self.rel.removesuffix(".ll").replace("/", "__")


def entry(rel: str) -> Entry:
    """The corpus entry at `rel`, with its sidecar profile."""
    path = CORPUS / rel
    profile = path.with_suffix(".profile").read_text().strip()
    if profile not in PROFILE_FLAGS:
        raise ValueError(f"{rel}: unknown profile {profile!r}")
    return Entry(rel, profile)


def entries() -> list[Entry]:
    return [entry(str(p.relative_to(CORPUS)))
            for p in sorted(CORPUS.glob("*/*.ll"))]


def _run(argv: list, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True,
                          text=True, timeout=TOOL_TIMEOUT)


def compile_argv(tool: list[str], e: Entry, out: Path) -> list:
    """`tool` with the entry's profile flags: clang and rllvm get the same."""
    return [*tool, *PROFILE_FLAGS[e.profile], e.path, "-o", out]


def compile_entry(tool: list[str], e: Entry, out: Path) -> subprocess.CompletedProcess:
    return _run(compile_argv(tool, e, out))


def clang_compile(e: Entry, out: Path) -> Path:
    """The oracle object; a clang failure is a corpus bug."""
    r = compile_entry(["clang"], e, out)
    if r.returncode != 0:
        raise RuntimeError(f"clang {e.rel}: exit {r.returncode}: {r.stderr}")
    return out


def assemble(name: str, out: Path) -> Path:
    """corpus/extra/<name>.s with `as --64`: the entry's one razm object."""
    r = _run(["as", "--64", "-o", out, CORPUS / "extra" / f"{name}.s"])
    if r.returncode != 0:
        raise RuntimeError(f"as {name}.s: exit {r.returncode}: {r.stderr}")
    return out


def link_hosted(objs: list[Path], out: Path) -> subprocess.CompletedProcess:
    """link_hosted's shape: `clang -nostdlib`, the runtime object first."""
    return _run(["clang", "-nostdlib", *objs, "-o", out])


def link_pie(objs: list[Path], out: Path) -> subprocess.CompletedProcess:
    """link_freestanding_elf for a `pic` bin."""
    return _run(["ld.lld", "--pie", "--no-dynamic-linker", *objs, "-o", out])


def link_script(script: str, objs: list[Path], out: Path) -> subprocess.CompletedProcess:
    """link_freestanding_elf with `-T` corpus/<script>."""
    return _run(["ld.lld", "-T", CORPUS / script, *objs, "-o", out])


@dataclass(frozen=True)
class RunResult:
    stdout: bytes
    status: int


def run(binary: Path) -> RunResult:
    r = subprocess.run([str(binary)], capture_output=True, timeout=TOOL_TIMEOUT)
    return RunResult(r.stdout, r.returncode)


def mnemonics(obj: Path) -> set[str]:
    """Every mnemonic `objdump -d -M suffix` prints for `obj`."""
    r = _run(["objdump", "-d", "-M", "suffix", "--no-show-raw-insn", obj])
    if r.returncode != 0:
        raise RuntimeError(f"objdump {obj}: {r.stderr}")
    seen = set()
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and line.startswith(" ") and parts[1].strip():
            seen.add(parts[1].split()[0])
    return seen


def missing_mnemonics(obj: Path, wanted: list[str]) -> list[str]:
    """The `wanted` mnemonics `obj`'s disassembly does not show."""
    seen = mnemonics(obj)
    missing = []
    for m in wanted:
        names = {m} | OBJDUMP_ALIASES.get(m, set())
        if m == "pclmulqdq":   # objdump names the immediate's form
            if any(s.startswith("pclmul") and s.endswith("qdq") for s in seen):
                continue
        if not names & seen:
            missing.append(m)
    return missing


def definitions(binary: Path, name: str) -> int:
    """How many defined symbols named `name` `nm` lists in `binary`."""
    r = _run(["nm", "--defined-only", binary])
    if r.returncode != 0:
        raise RuntimeError(f"nm {binary}: {r.stderr}")
    return sum(1 for line in r.stdout.splitlines() if line.split()[-1:] == [name])


# --- ELF64 relocations ----------------------------------------------------

SHT_SYMTAB = 2
SHT_RELA = 4
SHF_WRITE = 0x1
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4
STB_LOCAL = 0
SHN_UNDEF = 0


@dataclass(frozen=True)
class ElfSymbol:
    name: str
    binding: int
    shndx: int


@dataclass(frozen=True)
class Reloc:
    section: str           # the section the relocation applies to
    exec: bool             # that section is SHF_EXECINSTR
    offset: int
    type: int
    symbol: ElfSymbol


@dataclass(frozen=True)
class ElfInfo:
    symbols: list[ElfSymbol]
    relocs: list[Reloc]

    def undefined(self) -> set[str]:
        return {s.name for s in self.symbols if s.shndx == SHN_UNDEF and s.name}


def read_elf(path: Path) -> ElfInfo:
    """The symbols and RELA relocations of a relocatable ELF64 object."""
    data = path.read_bytes()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise ValueError(f"{path}: not a little-endian ELF64 file")
    shoff, = struct.unpack_from("<Q", data, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    shdrs = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * shentsize)
             for i in range(shnum)]

    def strtab(index: int, off: int) -> str:
        base = shdrs[index][4] + off
        return data[base:data.index(b"\0", base)].decode()

    names = [strtab(shstrndx, h[0]) for h in shdrs]
    symbols: list[ElfSymbol] = []
    symtab = next((i for i, h in enumerate(shdrs) if h[1] == SHT_SYMTAB), None)
    if symtab is not None:
        h = shdrs[symtab]
        for i in range(h[5] // 24):
            st_name, st_info, _, st_shndx = struct.unpack_from(
                "<IBBH", data, h[4] + i * 24)
            name = strtab(h[6], st_name) if st_name else ""
            if not name and st_info & 0xF == 3:   # a section symbol
                name = names[st_shndx]
            symbols.append(ElfSymbol(name, st_info >> 4, st_shndx))
    relocs = []
    for h in shdrs:
        if h[1] != SHT_RELA:
            continue
        target = shdrs[h[7]]
        for i in range(h[5] // 24):
            r_offset, r_info, _ = struct.unpack_from("<QQq", data, h[4] + i * 24)
            relocs.append(Reloc(names[h[7]], bool(target[2] & SHF_EXECINSTR),
                                r_offset, r_info & 0xFFFFFFFF,
                                symbols[r_info >> 32]))
    return ElfInfo(symbols, relocs)


def reloc_name(t: int) -> str:
    return RELOC_NAMES.get(t, f"type {t}")


_ASM_TEMPLATE = re.compile(r'asm sideeffect "([^"]*)"')
_ASM_SYMBOL = re.compile(r'\bcall\s+([A-Za-z_.$][\w.$]*)|([A-Za-z_.$][\w.$]*)\(%rip\)')


def asm_symbols(ll: Path) -> set[str]:
    """The symbols inline-asm templates in `ll` name: `call sym`, `sym(%rip)`."""
    names = set()
    for template in _ASM_TEMPLATE.findall(ll.read_text()):
        template = template.replace("\\0A", "\n")
        for call, rip in _ASM_SYMBOL.findall(template):
            names.add(call or rip)
    return names


def check_relocations(obj: Path, profile: str,
                      asm_syms: set[str] = frozenset()) -> list[str]:
    """Each relocation in `obj` the profile's row does not allow for its use.

    In a data section every relocation is a pointer in an initializer,
    R_X86_64_64. In code it is the row's external-data, internal-data or
    call type, or PC32 / PLT32 against a symbol an inline-asm template names
    (`asm_syms`), or the stack protector's PC32 guard load; a GOT load names
    a symbol that is not local. No profile writes R_X86_64_32.
    """
    rule = RELOC_RULES[RELOC_PROFILE[profile]]
    allowed = {rule.external_data, rule.internal_data} | rule.calls
    bad = []
    for r in read_elf(obj).relocs:
        where = f"{r.section}+{r.offset:#x} {reloc_name(r.type)} {r.symbol.name}"
        if r.section.startswith(".eh_frame"):
            continue
        if not r.exec:
            if r.type != R_X86_64_64:
                bad.append(f"{where}: data initializers are R_X86_64_64")
        elif r.type not in allowed and not (
                r.type in ASM_TEMPLATE_RELOCS and r.symbol.name in asm_syms) \
                and not (r.type == R_X86_64_PC32 and r.symbol.name == STACK_GUARD):
            bad.append(f"{where}: not in the {RELOC_PROFILE[profile]} profile")
        elif r.type == R_X86_64_REX_GOTPCRELX and r.symbol.binding == STB_LOCAL:
            bad.append(f"{where}: internal data through the GOT")
    return bad
