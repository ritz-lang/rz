#!/bin/bash
# Golden stdout for elf_demo (examples/tier5_async/84_elf), AGAST #1463.
# Run by scripts/regression.sh once per compiler, with CWD=pkg_dir and
# ./elf_demo linked to that compiler's build.
set -uo pipefail

want=$(cat <<'GOLDEN'
read /proc/self/exe: ok
elf_init: 0
class: ELF64
data: little-endian
machine: 62 (x86-64)
section .text: yes
section .symtab: yes
section .no_such_section: no
elf_parse_sections: 0
symbols > 0: 1
main is a global function: 1
read_u16/u32/u64: 513 67305985 578437695752307201
elf_init on 16 bytes: -1
elf_init on bad magic: -1
GOLDEN
)
out=$(./elf_demo </dev/null); rc=$?
if [[ "$rc" != 0 ]]; then
    echo "FAIL: elf_demo: exit $rc, want 0" >&2
    exit 1
fi
if [[ "$out" != "$want" ]]; then
    echo "FAIL: elf_demo: stdout" >&2
    diff <(echo "$want") <(echo "$out") >&2
    exit 1
fi
echo "elf_demo: all cases passed"
