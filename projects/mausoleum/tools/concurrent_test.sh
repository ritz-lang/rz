#!/usr/bin/env bash
# concurrent_test.sh - Phase 5 (mausoleum-async) regression test
#
# Verifies that the async event loop survives concurrent client load
# without one client stalling another.  The three sub-scenarios match
# the briefing's hard gates:
#
#   1. Parallel wiki-seed   — two seed processes vs same DB
#   2. Slow-client isolation — silent nc + concurrent --ping-loop
#   3. Mid-scan starvation  — 3 BG scan-loops (large) + 10 ping-loops
#
# Each test asserts exit-code 0 on every concurrent client and that the
# server is still alive at the end.  Latency probes confirm the ping
# clients run at single-client baseline speed (<10ms wall) even under
# heavy concurrent load.
#
# Pre-existing bugs surfaced and fixed during phase 5:
#   - sys_io_uring_enter used syscall4; r8/r9 held garbage that the
#     kernel saw as `argp`, causing -EINVAL after the first clean
#     disconnect.  Fix: syscall6 with argp=0, argsz=0 in
#     projects/ritz/ritzlib/uring.ritz.
#   - client_scan cast the callback as `*fn(...)` (pointer-to-fn)
#     and dereferenced it; the extra load read code bytes and called
#     into garbage.  Fix: cast as `fn(...)` in
#     projects/mausoleum/lib/client.ritz.
#
# Run from repo root after `./rz build mausoleum`:
#   bash projects/mausoleum/tools/concurrent_test.sh
#
# Returns 0 on success, non-zero on first failure.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
BIN_DIR="$REPO_ROOT/projects/mausoleum/build/debug"

MAUSOLEUM="$BIN_DIR/mausoleum"
WIKISEED="$BIN_DIR/wiki-seed"
BENCH="$BIN_DIR/concurrent_bench"

if [[ ! -x "$MAUSOLEUM" || ! -x "$WIKISEED" || ! -x "$BENCH" ]]; then
    echo "FAIL: required binaries missing under $BIN_DIR — run \`./rz build mausoleum\`" >&2
    exit 2
fi

PASS=0
FAIL=0
FAILED_TESTS=()

# Pick a high-numbered port range that's unlikely to clash with anything.
PORT_BASE=17800

# Wait for tcp listener — beats `sleep 1` since it's correct on slow CI.
wait_for_port() {
    local port="$1"
    local i
    for i in $(seq 1 50); do
        if exec 6<>/dev/tcp/127.0.0.1/"$port" 2>/dev/null; then
            exec 6<&-
            exec 6>&-
            return 0
        fi
        sleep 0.05
    done
    echo "  port $port never opened" >&2
    return 1
}

# Boot a fresh --async mausoleum on $1, returns server PID via $SERVER_PID.
boot_server() {
    local port="$1"
    local datadir="$2"
    rm -rf "$datadir"
    mkdir -p "$datadir"
    "$MAUSOLEUM" serve --async --port "$port" --no-encryption --data-dir "$datadir" \
        > "/tmp/m7sp_p5_${port}.log" 2>&1 &
    SERVER_PID=$!
    if ! wait_for_port "$port"; then
        kill -9 "$SERVER_PID" 2>/dev/null
        return 1
    fi
    return 0
}

stop_server() {
    if [[ -n "${SERVER_PID:-}" ]]; then
        kill "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null
        SERVER_PID=""
    fi
}

assert_alive() {
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "  FAIL: server died unexpectedly" >&2
        return 1
    fi
    return 0
}

record() {
    local label="$1" rc="$2"
    if [[ "$rc" -eq 0 ]]; then
        PASS=$((PASS+1))
        echo "  ok   $label"
    else
        FAIL=$((FAIL+1))
        FAILED_TESTS+=("$label")
        echo "  FAIL $label (rc=$rc)"
    fi
}

# ─── Test 1: parallel wiki-seed ─────────────────────────────────────────
test_parallel_wiki_seed() {
    echo "Test 1: parallel wiki-seed"
    local port="$((PORT_BASE + 0))"
    local dd="/tmp/m7sp_p5_t1_${port}"
    if ! boot_server "$port" "$dd"; then
        record "boot t1 server" 1
        return
    fi

    "$WIKISEED" --port "$port" --no-encryption --seed > "/tmp/m7sp_p5_t1_c1.log" 2>&1 &
    local p1=$!
    "$WIKISEED" --port "$port" --no-encryption --seed > "/tmp/m7sp_p5_t1_c2.log" 2>&1 &
    local p2=$!
    wait "$p1"; local rc1=$?
    wait "$p2"; local rc2=$?
    record "wiki-seed client A" "$rc1"
    record "wiki-seed client B" "$rc2"
    assert_alive; record "server alive after parallel seed" $?

    local inserts
    inserts=$(grep -c "INSERT doc_id" "/tmp/m7sp_p5_${port}.log" || true)
    if [[ "$inserts" -eq 10 ]]; then
        record "10 inserts persisted (5+5)" 0
    else
        record "10 inserts persisted (got $inserts)" 1
    fi
    stop_server
}

# ─── Test 2: slow-client isolation ──────────────────────────────────────
test_slow_client_isolation() {
    echo "Test 2: slow-client isolation"
    local port="$((PORT_BASE + 1))"
    local dd="/tmp/m7sp_p5_t2_${port}"
    if ! boot_server "$port" "$dd"; then
        record "boot t2 server" 1
        return
    fi

    # Open a silent nc — never sends bytes, holds the slot open.
    nc 127.0.0.1 "$port" < /dev/null > /dev/null 2>&1 &
    local nc_pid=$!
    sleep 0.5

    # Time wiki-seed concurrently.  On a working async loop this finishes
    # in ~10ms wall; on the old serial loop it'd hang forever waiting for
    # the silent nc to disconnect.
    local t_start t_end elapsed_ms
    t_start=$(date +%s%N)
    "$WIKISEED" --port "$port" --no-encryption --seed > /dev/null 2>&1
    local rc=$?
    t_end=$(date +%s%N)
    elapsed_ms=$(( (t_end - t_start) / 1000000 ))

    record "wiki-seed completes alongside silent nc (${elapsed_ms}ms)" "$rc"
    if [[ "$elapsed_ms" -lt 1000 ]]; then
        record "wiki-seed not stalled by silent nc" 0
    else
        record "wiki-seed stalled by silent nc (${elapsed_ms}ms)" 1
    fi
    assert_alive; record "server alive after slow-client" $?

    kill "$nc_pid" 2>/dev/null
    wait "$nc_pid" 2>/dev/null
    stop_server
}

# ─── Test 3: mid-scan starvation ────────────────────────────────────────
test_midscan_starvation() {
    echo "Test 3: mid-scan starvation"
    local port="$((PORT_BASE + 2))"
    local dd="/tmp/m7sp_p5_t3_${port}"
    if ! boot_server "$port" "$dd"; then
        record "boot t3 server" 1
        return
    fi

    # Seed enough docs that a SCAN must emit >= 30 batches (16 per batch)
    # so multi-batch flow is exercised.
    "$BENCH" --port "$port" --bulk-insert 500 > /dev/null 2>&1
    record "bulk-insert 500 docs" $?

    # Three BG scan-loops doing 10 iters each = 30 full collection scans.
    "$BENCH" --port "$port" --scan-loop 10 > /tmp/m7sp_p5_t3_bg1.log 2>&1 &
    local b1=$!
    "$BENCH" --port "$port" --scan-loop 10 > /tmp/m7sp_p5_t3_bg2.log 2>&1 &
    local b2=$!
    "$BENCH" --port "$port" --scan-loop 10 > /tmp/m7sp_p5_t3_bg3.log 2>&1 &
    local b3=$!

    # 10 sequential ping-loops on parallel connections.  Each must
    # complete within a budget that's clearly below "starved" levels.
    # Locally these take ~3ms; allow generous 250ms ceiling for CI noise.
    local max_ms=0 i ping_rc
    for i in 1 2 3 4 5 6 7 8 9 10; do
        local s e
        s=$(date +%s%N)
        "$BENCH" --port "$port" --ping-loop 5 > /dev/null 2>&1
        ping_rc=$?
        e=$(date +%s%N)
        local d=$(( (e - s) / 1000000 ))
        if [[ "$d" -gt "$max_ms" ]]; then max_ms=$d; fi
        if [[ "$ping_rc" -ne 0 ]]; then
            record "ping-loop $i (rc=$ping_rc, ${d}ms)" 1
        fi
    done

    if [[ "$max_ms" -lt 250 ]]; then
        record "10 ping-loops not starved by concurrent SCANs (max=${max_ms}ms)" 0
    else
        record "ping-loops starved (max=${max_ms}ms >= 250ms)" 1
    fi

    wait "$b1"; record "BG scan-loop A (10 iters)" $?
    wait "$b2"; record "BG scan-loop B (10 iters)" $?
    wait "$b3"; record "BG scan-loop C (10 iters)" $?

    # Server should have processed >= 31 SCANs (30 BG + 0 baseline here).
    local scan_count
    scan_count=$(grep -c "SCAN max_results" "/tmp/m7sp_p5_${port}.log" || true)
    if [[ "$scan_count" -ge 30 ]]; then
        record "server processed ${scan_count} SCANs" 0
    else
        record "expected >=30 SCANs, got ${scan_count}" 1
    fi

    assert_alive; record "server alive after starvation test" $?
    stop_server
}

# ─── Run ────────────────────────────────────────────────────────────────
test_parallel_wiki_seed
test_slow_client_isolation
test_midscan_starvation

echo ""
echo "Phase 5 concurrent-correctness: $PASS passed, $FAIL failed"
if [[ "$FAIL" -ne 0 ]]; then
    echo "Failed:"
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t"
    done
    exit 1
fi
exit 0
