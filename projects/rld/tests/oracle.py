"""rld's oracle driver: link the same objects with `ld.lld` and with rld, run
both, and compare (../../razm/DESIGN.md "rld tests").

The no-script executable is the `rzrz` shape: `link_freestanding_elf` with no
`-T` and no `--pie`, the clang-built `ritz_start.x86_64.o` first. Objects
come from every producer rld reads: `clang -c` with the flags
`freestanding_target` gives a `x86_64-unknown-linux-gnu` bin, rllvm with the
same flags, `as --64`, and razm.

The driver shells out to clang, as, ld.lld, objdump and the tools under
test, and reads ELF headers itself. It does not import build_pipeline.py.
"""

from __future__ import annotations

import os
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus"
PROJECTS = HERE.parent.parent
RLLVM_CORPUS = PROJECTS / "rllvm" / "tests" / "corpus"

TOOL_TIMEOUT = 60  # seconds, per compile / link / run

# freestanding_target for a [[bin]] with target = "x86_64-unknown-linux-gnu"
# (rzrz, rzsh.linux): no -fPIC, which clang 21 makes PIE code anyway.
RZRZ_FLAGS = ["-c", "--target=x86_64-unknown-linux-gnu", "-ffreestanding",
              "-fno-builtin", "-march=native", "-msha"]
# ensure_runtime_object: the shim is `clang -c` with nothing else.
SHIM_FLAGS = ["-c"]

PT_LOAD = 1
PF_X, PF_W, PF_R = 1, 2, 4


def tool(env: str, pkg: str, name: str) -> Path | None:
    """A ritz-built tool: $ENV, else its package's debug build, else None."""
    path = Path(os.environ.get(env) or PROJECTS / pkg / "build" / "debug" / name)
    return path if os.access(path, os.X_OK) else None


def run_tool(argv: list, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True,
                          text=True, timeout=TOOL_TIMEOUT)


def must(argv: list) -> None:
    r = run_tool(argv)
    if r.returncode != 0:
        raise RuntimeError(f"{argv[0]}: exit {r.returncode}: {r.stderr}")


def compile_ll(compiler: Path | str, src: Path, flags: list[str], out: Path) -> Path:
    must([compiler, *flags, src, "-o", out])
    return out


def assemble(assembler: Path | str, src: Path, out: Path, extra: list[str] = ()) -> Path:
    must([assembler, "--64", *extra, "-o", out, src])
    return out


def link_lld(objs: list[Path], out: Path) -> subprocess.CompletedProcess:
    """link_freestanding_elf with no script and no --pie."""
    return run_tool(["ld.lld", "-o", out, *objs])


def link_rld(rld: Path, objs: list[Path], out: Path) -> subprocess.CompletedProcess:
    return run_tool([rld, "-o", out, *objs])


@dataclass(frozen=True)
class RunResult:
    stdout: bytes
    status: int


def run(binary: Path) -> RunResult:
    r = subprocess.run([str(binary)], capture_output=True, timeout=TOOL_TIMEOUT)
    return RunResult(r.stdout, r.returncode)


@dataclass(frozen=True)
class Segment:
    ptype: int
    flags: int
    offset: int
    vaddr: int
    paddr: int
    filesz: int
    memsz: int
    align: int


@dataclass(frozen=True)
class Executable:
    etype: int
    entry: int
    segments: list[Segment]
    sections: dict[str, tuple[int, int]]    # name: (address, size)
    symbols: dict[str, list[int]]           # defined global: its addresses


def read_executable(path: Path) -> Executable:
    data = path.read_bytes()
    assert data[:4] == b"\x7fELF", f"{path}: not ELF"
    etype, = struct.unpack_from("<H", data, 16)
    entry, phoff, shoff = struct.unpack_from("<QQQ", data, 24)
    phentsize, phnum, shentsize, shnum, shstrndx = struct.unpack_from("<HHHHH", data, 54)
    segments = [Segment(*struct.unpack_from("<IIQQQQQQ", data, phoff + i * phentsize))
                for i in range(phnum)]
    headers = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * shentsize)
               for i in range(shnum)]

    def name_at(table: int, at: int) -> str:
        off = headers[table][4] + at
        return data[off:data.index(b"\0", off)].decode()

    sections, symbols = {}, {}
    for h in headers[1:]:
        sections[name_at(shstrndx, h[0])] = (h[3], h[5])
    for h in headers:
        if h[1] != 2:   # SHT_SYMTAB
            continue
        for i in range(1, h[5] // 24):
            name, info, _, shndx, value, _ = struct.unpack_from("<IBBHQQ", data, h[4] + i * 24)
            if info >> 4 != 0 and shndx != 0:
                symbols.setdefault(name_at(h[6], name), []).append(value)
    return Executable(etype, entry, segments, sections, symbols)


def mnemonics(binary: Path, section: str = ".text") -> list[str]:
    """The instruction mnemonics of `section`, in order."""
    r = run_tool(["objdump", "-d", "-j", section, "--no-show-raw-insn", binary])
    if r.returncode != 0:
        raise RuntimeError(f"objdump {binary}: {r.stderr}")
    out = []
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and line.startswith(" ") and parts[1].strip():
            out.append(parts[1].split()[0])
    return out
