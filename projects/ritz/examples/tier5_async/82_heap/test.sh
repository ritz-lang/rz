#!/bin/bash
# Golden stdout for heap_demo (examples/tier5_async/82_heap), AGAST #1463.
# Run by scripts/regression.sh once per compiler, with CWD=pkg_dir and
# ./heap_demo linked to that compiler's build.
set -uo pipefail

want=$(cat <<'GOLDEN'
push 3: valid=1
push 1: valid=1
push 4: valid=1
push 1: valid=1
push 5: valid=1
pushed: 5
sum via heap_get: 14
pop 0: 3 (valid after drop: 0)
pop 1: 1 (valid after drop: 0)
pop 2: 4 (valid after drop: 0)
pop 3: 1 (valid after drop: 0)
pop 4: 5 (valid after drop: 0)
popped: 5
set 7 -> get: 7
as_ptr write 9 -> get: 9
method get: 9
method set 11 -> get: 11
double drop safe: 0
point: 3,4
GOLDEN
)
out=$(./heap_demo </dev/null); rc=$?
if [[ "$rc" != 0 ]]; then
    echo "FAIL: heap_demo: exit $rc, want 0" >&2
    exit 1
fi
if [[ "$out" != "$want" ]]; then
    echo "FAIL: heap_demo: stdout" >&2
    diff <(echo "$want") <(echo "$out") >&2
    exit 1
fi
echo "heap_demo: all cases passed"
