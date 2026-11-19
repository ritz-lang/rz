#!/bin/bash
# Golden stdout for process_demo (examples/tier5_async/80_process):
# ritzlib.process (AGAST #1461; StrView / Span API since #1481).  Children are
# /bin/cat and sh, found through find_command ($PATH, or the standard
# directories without one).  No PIDs are printed, so the output is the same on
# every run and under both compilers.
#
# Run by scripts/regression.sh once per compiler, with CWD=pkg_dir and
# ./process_demo linked to that compiler's build.
set -uo pipefail

want=$(cat <<'GOLDEN'
== read all ==
spawned: 1
wrote: 6
wrote: 6
stdout: [alpha\nbravo\n] (12)
exit: 0
success: 1
signaled: 0
wait again: ECHILD
== read by line ==
line 1: [alpha\n] (6)
line 2: [bravo] (5)
eof: [] (0)
exit: 0
== exit code ==
sh found: 1
exit: 3
success: 0
signaled: 0
== kill ==
exit: 137
success: 0
signaled: 1
signal: 9
== missing ==
not found: 1
GOLDEN
)
out=$(./process_demo </dev/null); rc=$?
if [[ "$rc" != 0 ]]; then
    echo "FAIL: process_demo: exit $rc, want 0" >&2
    exit 1
fi
if [[ "$out" != "$want" ]]; then
    echo "FAIL: process_demo: stdout" >&2
    diff <(echo "$want") <(echo "$out") >&2
    exit 1
fi
echo "process_demo: all cases passed"
