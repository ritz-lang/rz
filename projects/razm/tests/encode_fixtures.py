#!/usr/bin/env python3
"""The encode tests' expected bytes, from `as --64`.

Each case in test/test_encode_*.ritz is a call

    check(Code64, "addq $8, %rsp", "48 83 c4 08", ins2(...))

(or check_short, or check_err with no expected string). This script
assembles every case's text with `as --64` in its .code mode and writes what
`as` produced into the expected string: the bytes in hex, then
` | offset:kindwidth:target+addend` per relocation (test/support/check.ritz
renders razm's output the same way). A check_err case must be rejected by
`as` too.

`L` is a label on the case's first byte. A `check` (near form) of a branch to
`L` is assembled with `{disp32}` (`{disp16}` in .code16), which makes `as`
keep the near form.

    python3 tests/encode_fixtures.py          # rewrite the expected strings
    python3 tests/encode_fixtures.py --check  # exit 1 if any is stale
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle import RELOC_NAMES, read_elf  # noqa: E402

PKG = Path(__file__).resolve().parent.parent
TEST_GLOB = "test/test_encode_*.ritz"

CASE = re.compile(
    r'\b(check|check_short|check_err)\(\s*(Code16|Code32|Code64),\s*'
    r'"((?:[^"\\]|\\.)*)"(?:,\s*"((?:[^"\\]|\\.)*)")?')

# A relocation type as the fixture spells the fixup that makes it.
FIXUP_NAMES = {
    "R_X86_64_8": "abs1", "R_X86_64_16": "abs2", "R_X86_64_32": "abs4",
    "R_X86_64_64": "abs8", "R_X86_64_32S": "sabs4", "R_X86_64_PC8": "pc1",
    "R_X86_64_PC16": "pc2", "R_X86_64_PC32": "pc4", "R_X86_64_PLT32": "plt4",
    "R_X86_64_REX_GOTPCRELX": "gotx4",
}


MAX_LINE = 100
# A case on one line, split before its instruction when it is too long.
ONE_LINE = re.compile(
    r'^(\s*)(n \+= check(?:_short)?\(Code\d+, "(?:[^"\\]|\\.)*", "[^"]*",'
    r'|n \+= check_err\(Code\d+, "(?:[^"\\]|\\.)*",) (.*)$')


def wrap(src: str) -> str:
    """Each case line longer than MAX_LINE, split before its instruction."""
    out = []
    for line in src.split("\n"):
        m = ONE_LINE.match(line)
        if m and len(line) > MAX_LINE:
            indent, head, rest = m.groups()
            out.append(f"{indent}{head}\n{indent}    {rest}")
        else:
            out.append(line)
    return "\n".join(out)


@dataclass
class Case:
    path: Path
    func: str
    mode: str
    text: str
    want: str | None
    want_span: tuple[int, int] | None   # where `want` sits in the file


def cases(paths: list[Path]) -> list[Case]:
    out = []
    for path in paths:
        src = path.read_text(encoding="utf-8")
        for m in CASE.finditer(src):
            func, mode, text, want = m.groups()
            if func == "check_err" and want is not None:
                raise SystemExit(f"{path}: check_err takes no expected string: {text}")
            if func != "check_err" and want is None:
                raise SystemExit(f"{path}: {func} needs an expected string: {text}")
            span = m.span(4) if want is not None else None
            out.append(Case(path, func, mode, text, want, span))
    return out


def source_of(case: Case) -> str:
    text = case.text.replace('\\"', '"').replace("\\\\", "\\")
    bits = case.mode.removeprefix("Code")
    if case.func == "check" and re.search(r"\bL\b", text):
        text = ("{disp16} " if bits == "16" else "{disp32} ") + text
    return f".text\n.code{bits}\nL: {text}\n"


def assemble(case: Case) -> str | None:
    """`as`'s bytes and relocations for the case; None if `as` rejects it."""
    with tempfile.TemporaryDirectory() as d:
        s, o = Path(d) / "case.s", Path(d) / "case.o"
        s.write_text(source_of(case), encoding="utf-8")
        p = subprocess.run(["as", "--64", "-o", str(o), str(s)],
                           capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            return None
        obj = read_elf(o.read_bytes())
    text = next(sec for sec in obj.sections if sec.name == ".text")
    parts = [" ".join(f"{b:02x}" for b in text.data)]
    for r in obj.relocs:
        if r.section != ".text":
            continue
        name = RELOC_NAMES.get(r.type, str(r.type))
        parts.append(f"{r.offset}:{FIXUP_NAMES.get(name, name)}:{r.symbol.name}{r.addend:+d}")
    return " | ".join(parts)


def run(paths: list[Path], check: bool) -> list[str]:
    """The problems found; rewrites stale expected strings unless `check`."""
    all_cases = cases(paths)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(assemble, all_cases))
    problems, edits = [], {}
    for case, got in zip(all_cases, results):
        where = f"{case.path.name}: .code{case.mode[4:]} {case.text}"
        if case.func == "check_err":
            if got is not None:
                problems.append(f"{where}: as accepts it ({got})")
            continue
        if got is None:
            problems.append(f"{where}: as rejects it")
            continue
        if got != case.want:
            if check:
                problems.append(f"{where}:\n    fixture: {case.want}\n    as:      {got}")
            else:
                edits.setdefault(case.path, []).append((case.want_span, got))
    for path in paths:
        src = path.read_text(encoding="utf-8")
        for (start, end), got in sorted(edits.get(path, []), reverse=True):
            src = src[:start] + got + src[end:]
        if not check:
            src = wrap(src)
        if src != path.read_text(encoding="utf-8"):
            path.write_text(src, encoding="utf-8")
    return problems


def main(argv: list[str]) -> int:
    check = "--check" in argv
    paths = sorted(PKG.glob(TEST_GLOB))
    problems = run(paths, check)
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
