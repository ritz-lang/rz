#!/usr/bin/env python3
"""Fail if a kernel binary addresses memory below %rsp (AGAST #4308).

In ring 0 an interrupt or exception taken on the current stack (IST 0)
pushes its frame just below %rsp: anything a function kept there (the
x86-64 red zone) is clobbered. harland's [[bin]] sets `no-red-zone = true`
and the compiler marks every function `noredzone`; this checks the result
on the linked binary, so a regression in any layer (build.py not passing
--no-red-zone, an emitter path skipping the attribute, an assembly file
using the red zone) fails the boot test.

    check_no_red_zone.py BINARY      exit 0 clean, 1 red zone used, 2 error
"""

import re
import subprocess
import sys
from typing import Dict, List

_FN = re.compile(r"^[0-9a-f]+ <(.+)>:$")
# A memory operand with a negative displacement off %rsp: -0x8(%rsp),
# -0x10(%rsp,%rax,8).
_BELOW_RSP = re.compile(r"-0x[0-9a-f]+\(%rsp[,)]")


def red_zone_functions(disassembly: str) -> Dict[str, List[str]]:
    """{function: its instructions that address below %rsp}, from
    `objdump -d --no-show-raw-insn` output."""
    found: Dict[str, List[str]] = {}
    fn = "?"
    for line in disassembly.splitlines():
        m = _FN.match(line)
        if m:
            fn = m.group(1)
            continue
        if _BELOW_RSP.search(line):
            insn = line.split("\t", 1)[-1].strip()
            found.setdefault(fn, []).append(insn)
    return found


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    try:
        dis = subprocess.run(["objdump", "-d", "--no-show-raw-insn", argv[1]],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"check_no_red_zone: objdump failed on {argv[1]}: {e}", file=sys.stderr)
        return 2
    found = red_zone_functions(dis)
    if not found:
        print(f"check_no_red_zone: {argv[1]}: no red zone use")
        return 0
    n = sum(len(v) for v in found.values())
    print(f"FAIL: {argv[1]} uses the red zone: {n} instruction(s) in "
          f"{len(found)} function(s) address memory below %rsp")
    for fn, insns in sorted(found.items())[:20]:
        print(f"  {fn}: {insns[0]}" + (f" (+{len(insns) - 1})" if len(insns) > 1 else ""))
    if len(found) > 20:
        print(f"  ... and {len(found) - 20} more")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
