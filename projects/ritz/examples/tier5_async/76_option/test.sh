#!/bin/bash
# Golden stdout for option_demo (examples/tier5_async/76_option): every
# ritzlib.option idiom (AGAST #1460).
#
# Run by scripts/regression.sh once per compiler, with CWD=pkg_dir and
# ./option_demo linked to that compiler's build.
set -uo pipefail

want='is_some(some): 1
is_none(some): 0
is_some(none): 0
is_none(none): 1
unwrap_or(some, 0): 42
unwrap_or(none, 99): 99
match some: 5
match none: 7
describe(some): 40
describe(none): -1
find(6) is_some: 1
find(5) is_none: 1
find(6): 6
find(5): -1
describe(find(9)): 90
describe(find(8)): -1
find(3).unwrap_or(-1): 3
find(4).unwrap_or(-1): -1
some.unwrap_or(0): 11
none.unwrap_or(5): 5
is_some(point): 1
is_none(point): 1
point_sum(some): 7
point_sum(none): 0
match point.x: 3
match none point.y: -1'

out=$(./option_demo); rc=$?
[[ "$rc" == 0 ]] || { echo "FAIL: option_demo exit $rc, want 0" >&2; exit 1; }
if [[ "$out" != "$want" ]]; then
    echo "FAIL: option_demo stdout" >&2
    diff <(echo "$want") <(echo "$out") >&2
    exit 1
fi
echo "option_demo: all cases passed"
