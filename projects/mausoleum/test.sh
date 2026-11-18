#!/bin/bash
# Integer arguments through the real binaries (AGAST #1957, #4039).
#
# `mausoleum shell --port N` echoes N through src/main.ritz's print_i32
# before it tries to connect; its old digit loop negated with `v = -v`,
# which wraps for i32's minimum, so -2147483648 printed as a bare "-" (#1957).
# Nothing listens on 127.0.0.1 port 0 or below, so the connect fails at
# once; timeout guards the case where it doesn't.
#
# The integer arguments of mausoleum, wiki-seed and concurrent_bench go
# through cliarg_parse_i32 (#4039).  Their old loops skipped non-digits and
# wrapped: "--port 2147483648" connected to port -2147483648 and "12x" to 12.
# Out-of-range or non-numeric values must now be refused before connecting.
set -u
cd "$(dirname "$0")"
B=$PWD/build/debug
for b in mausoleum wiki-seed concurrent_bench; do
    [ -x "$B/$b" ] || { echo "FAIL: $B/$b not built"; exit 1; }
done
fails=0
fail() { echo "FAIL: $*"; fails=$((fails+1)); }

# Accepted: the shell echoes the port it parsed.
for case in "0 0" "2147483647 2147483647" "-2147483648 -2147483648"; do
    set -- $case
    out=$(timeout 10 "$B/mausoleum" shell --host 127.0.0.1 --port "$1" 2>&1 </dev/null)
    if grep -qF -- "Connecting to 127.0.0.1:$2," <<<"$out"; then
        echo "ok: port $1 prints $2"
    else
        fail "port $1 should print $2: $out"
    fi
done

# Refused: "ERROR: invalid <flag> value", the tool's usage exit code (so
# not a timeout from a server that started anyway), no connect.
refused() {  # <flag> <cmd...>
    local flag=$1; shift
    local want=2 out rc
    [ "${1##*/}" = wiki-seed ] && want=1
    out=$(timeout 10 "$@" 2>&1 </dev/null); rc=$?
    if [ $rc -eq $want ] && grep -qF -- "invalid $flag value" <<<"$out" \
        && ! grep -qiE "connecting|connect failed|error code" <<<"$out"; then
        echo "ok: refused: ${*:2}"
    else
        fail "should refuse (rc=$rc, want $want): ${*:2}: $out"
    fi
}
for v in 2147483648 -2147483649 9223372036854775808 12x abc; do
    refused --port "$B/mausoleum" shell --host 127.0.0.1 --port "$v"
    refused --port "$B/mausoleum" serve --port "$v"
    refused --port "$B/wiki-seed" --port "$v" --verify
    refused --port "$B/concurrent_bench" --port "$v" --ping-loop 1
done
refused --bulk-insert "$B/concurrent_bench" --port 1 --bulk-insert 2147483648
refused --ping-loop "$B/concurrent_bench" --port 1 --ping-loop 9223372036854775808
refused --scan-loop "$B/concurrent_bench" --port 1 --scan-loop 3x

# Accepted by the tools: they get as far as the (failing) connect.
for cmd in "wiki-seed --port 2147483647 --verify" \
           "concurrent_bench --port 2147483647 --ping-loop 1" \
           "concurrent_bench --port 1 --bulk-insert -2147483648"; do
    out=$(timeout 10 $B/$cmd 2>&1 </dev/null)
    if grep -qiE "error code|connect failed" <<<"$out" && ! grep -qF invalid <<<"$out"; then
        echo "ok: accepted: $cmd"
    else
        fail "should parse and try to connect: $cmd: $out"
    fi
done
[ $fails -eq 0 ]
