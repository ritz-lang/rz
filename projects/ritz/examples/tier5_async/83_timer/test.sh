#!/bin/bash
# Golden stdout for timer_demo (examples/tier5_async/83_timer), AGAST #1463.
# Run by scripts/regression.sh once per compiler, with CWD=pkg_dir and
# ./timer_demo linked to that compiler's build.
set -uo pipefail

want=$(cat <<'GOLDEN'
clock_gettime(MONOTONIC) ok: 1
tv_nsec in [0, 1e9): 1
timer_new zeroes start/end: 1
start/stop ok: 1 1
end >= start: 1
elapsed >= 0: 1
monotonic over 1000 reads: 1
CLOCK_REALTIME after 2020: 1
bad clock id is EINVAL: 1
stopwatch_new zeroes: 1
GOLDEN
)
out=$(./timer_demo </dev/null); rc=$?
if [[ "$rc" != 0 ]]; then
    echo "FAIL: timer_demo: exit $rc, want 0" >&2
    exit 1
fi
if [[ "$out" != "$want" ]]; then
    echo "FAIL: timer_demo: stdout" >&2
    diff <(echo "$want") <(echo "$out") >&2
    exit 1
fi
echo "timer_demo: all cases passed"
