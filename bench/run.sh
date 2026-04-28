#!/usr/bin/env bash
# bench/run.sh — End-to-end performance benchmark harness for the
# valet → zeus → nexus → mausoleum stack.
#
# Spins up every scenario in the matrix on its own port / Unix socket,
# fires `wrk` at it, captures throughput + latency percentiles, and
# prints a Markdown table.  Cleans up everything on exit (trap EXIT).
#
# Usage:
#   bench/run.sh                       # full matrix, default settings
#   bench/run.sh --duration 30         # longer run for tighter numbers
#   bench/run.sh --conns 200           # higher concurrency
#   bench/run.sh --skip mausoleum      # skip scenarios that need a DB
#   bench/run.sh --workers 4           # zeus -w N for proxy scenarios
#   bench/run.sh --json metrics.json   # also emit machine-readable JSON
#
# Requires: wrk, curl, bash, the binaries built via `./rz build PROJECT`.

set -euo pipefail

# ────────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────────

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH_DIR="$REPO_ROOT/bench"
BUILD_DIR="$REPO_ROOT/projects"

DURATION=10
CONNS=100
THREADS=4
WORKERS=1                # zeus worker count for proxy scenarios
SKIP=""
JSON_OUT=""
KEEP=0                   # if 1, leave servers running on exit

PORT_DIRECT=9001
PORT_STATIC=9002
PORT_PROXY=9003
PORT_PROXY_DB=9004
PORT_MAUSOLEUM=7777

SOCK_PROXY="/tmp/zeus_bench_inmem.sock"
SOCK_PROXY_DB="/tmp/zeus_bench_db.sock"

DATA_DIR_M7M="/tmp/m7m_bench_data"
LOG_DIR="/tmp/bench-logs"
mkdir -p "$LOG_DIR"

# ────────────────────────────────────────────────────────────────────
# Arg parsing
# ────────────────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --duration) DURATION="$2";  shift 2 ;;
        --conns)    CONNS="$2";     shift 2 ;;
        --threads)  THREADS="$2";   shift 2 ;;
        --workers)  WORKERS="$2";   shift 2 ;;
        --skip)     SKIP="$2";      shift 2 ;;
        --json)     JSON_OUT="$2";  shift 2 ;;
        --keep)     KEEP=1;         shift   ;;
        -h|--help)
            sed -n '/^# Usage:/,/^# Requires:/p' "$0" | sed 's/^# \?//'
            exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

# ────────────────────────────────────────────────────────────────────
# Utilities
# ────────────────────────────────────────────────────────────────────

PIDS=()
record_pid() { PIDS+=("$1"); }

cleanup() {
    if [[ "$KEEP" == "1" ]]; then
        echo "[bench] --keep: leaving servers running. PIDs: ${PIDS[*]}" >&2
        return
    fi
    for pid in "${PIDS[@]}"; do
        kill -9 "$pid" 2>/dev/null || true
    done
    # Belt and braces: also kill any of our debug binaries that linger.
    pkill -9 -f "$BUILD_DIR/.*/build/debug/(valet|nexus|zeus|mausoleum)" 2>/dev/null || true
    rm -f "$SOCK_PROXY" "$SOCK_PROXY_DB" 2>/dev/null || true
}
trap cleanup EXIT

# Render a config template, replacing BENCH_STATIC_ROOT with the
# absolute path of the bundled static dir.  Writes the rendered file
# next to the original with a `.rendered.json` suffix and echoes the
# rendered path.
render_static_config() {
    local src="$1"
    local dst="${src%.json}.rendered.json"
    sed "s|BENCH_STATIC_ROOT|$BENCH_DIR/static|g" "$src" > "$dst"
    echo "$dst"
}

# Wait until a TCP port is accepting connections (or unix socket exists).
# Args: port_or_path  timeout_seconds
wait_ready() {
    local target="$1" deadline=$(( $(date +%s) + ${2:-10} ))
    while [[ $(date +%s) -lt $deadline ]]; do
        if [[ "$target" == /* ]]; then
            [[ -S "$target" ]] && return 0
        else
            (echo > "/dev/tcp/127.0.0.1/$target") 2>/dev/null && return 0
        fi
        sleep 0.1
    done
    echo "[bench] timeout waiting for $target" >&2
    return 1
}

# Run wrk and emit JSON-ish key=value lines on stdout.  Args: name url
run_wrk() {
    local id="$1" name="$2" url="$3" log
    log=$(mktemp /tmp/bench-wrk-XXXXXX.log)
    wrk -t"$THREADS" -c"$CONNS" -d"${DURATION}s" --latency "$url" >"$log" 2>&1 || true

    local rps p50 p75 p90 p99 errors
    rps=$(awk '/Requests\/sec:/   { print $2 }' "$log" | head -1)
    p50=$(awk '/^ *50%/ { print $2 }' "$log" | head -1)
    p75=$(awk '/^ *75%/ { print $2 }' "$log" | head -1)
    p90=$(awk '/^ *90%/ { print $2 }' "$log" | head -1)
    p99=$(awk '/^ *99%/ { print $2 }' "$log" | head -1)
    errors=$(awk '/Socket errors:/ {print $0}' "$log" | head -1)
    [[ -z "$errors" ]] && errors="0"

    # Convert latency strings (`1.66ms`, `200.10us`, `1.10s`) to ms numbers.
    to_ms() {
        local v="$1"
        case "$v" in
            *us) awk -v s="${v%us}" 'BEGIN{ printf "%.3f", s/1000 }' ;;
            *ms) printf "%s" "${v%ms}" ;;
            *s)  awk -v s="${v%s}"  'BEGIN{ printf "%.3f", s*1000 }' ;;
            *)   printf "%s" "$v" ;;
        esac
    }

    p50_ms=$(to_ms "$p50")
    p75_ms=$(to_ms "$p75")
    p90_ms=$(to_ms "$p90")
    p99_ms=$(to_ms "$p99")

    # Print result line we'll later parse into the table.
    printf "RESULT id=%s rps=%s p50=%s p75=%s p90=%s p99=%s name=%q\n" \
        "$id" "${rps:-0}" "${p50_ms:-0}" "${p75_ms:-0}" "${p90_ms:-0}" "${p99_ms:-0}" "$name"

    rm -f "$log"
}

# ────────────────────────────────────────────────────────────────────
# Build (skip if binaries are present + newer than sources)
# ────────────────────────────────────────────────────────────────────

build_if_stale() {
    local proj="$1" bin="$2"
    local bin_path="$BUILD_DIR/$proj/build/debug/$bin"
    [[ -x "$bin_path" ]] || {
        echo "[bench] building $proj..." >&2
        ( cd "$REPO_ROOT" && ./rz build "$proj" >"$LOG_DIR/build-$proj.log" 2>&1 ) || {
            echo "[bench] build $proj FAILED — see $LOG_DIR/build-$proj.log" >&2
            return 1
        }
    }
}

build_if_stale valet     valet
build_if_stale zeus      zeus
build_if_stale nexus     nexus
build_if_stale mausoleum mausoleum
build_if_stale mausoleum wiki-seed

# ────────────────────────────────────────────────────────────────────
# Spin up all scenarios on different ports
# ────────────────────────────────────────────────────────────────────

cd "$REPO_ROOT"

# Shut down anything left over from a previous run.
pkill -9 -f "$BUILD_DIR/.*/build/debug/(valet|nexus|zeus|mausoleum)" 2>/dev/null || true
rm -f "$SOCK_PROXY" "$SOCK_PROXY_DB" 2>/dev/null || true
sleep 1

# A/B: valet direct (Hello World + JSON, both on the same valet)
echo "[bench] starting valet-direct on :$PORT_DIRECT" >&2
"$BUILD_DIR/valet/build/debug/valet" \
    -p "$PORT_DIRECT" -c "$BENCH_DIR/configs/valet-direct.json" \
    >"$LOG_DIR/v-direct.log" 2>&1 &
record_pid "$!"
wait_ready "$PORT_DIRECT" 5

# C: valet static (separate instance because static config differs)
echo "[bench] starting valet-static on :$PORT_STATIC" >&2
STATIC_CFG="$(render_static_config "$BENCH_DIR/configs/valet-static.json")"
"$BUILD_DIR/valet/build/debug/valet" \
    -p "$PORT_STATIC" -c "$STATIC_CFG" \
    >"$LOG_DIR/v-static.log" 2>&1 &
record_pid "$!"
wait_ready "$PORT_STATIC" 5

# D/E: zeus + nexus, in-memory (no mausoleum running) — proxied via valet:9003
if [[ "$SKIP" != *proxy* ]]; then
    echo "[bench] starting zeus + nexus (in-memory) on $SOCK_PROXY" >&2
    "$BUILD_DIR/zeus/build/debug/zeus" -f -v -w "$WORKERS" -m 1048576 -s "$SOCK_PROXY" \
        "$BUILD_DIR/nexus/build/debug/nexus" \
        >"$LOG_DIR/z-inmem.log" 2>&1 &
    record_pid "$!"
    wait_ready "$SOCK_PROXY" 8

    echo "[bench] starting valet-proxy on :$PORT_PROXY" >&2
    "$BUILD_DIR/valet/build/debug/valet" \
        -p "$PORT_PROXY" --zeus-socket "$SOCK_PROXY" \
        >"$LOG_DIR/v-inmem.log" 2>&1 &
    record_pid "$!"
    wait_ready "$PORT_PROXY" 5
fi

# F: zeus + nexus + mausoleum-serial — proxied via valet:9004
if [[ "$SKIP" != *mausoleum* ]] && [[ "$SKIP" != *proxy* ]]; then
    echo "[bench] starting mausoleum (serial) on :$PORT_MAUSOLEUM" >&2
    rm -rf "$DATA_DIR_M7M"; mkdir -p "$DATA_DIR_M7M"
    "$BUILD_DIR/mausoleum/build/debug/mausoleum" serve --serial \
        --port "$PORT_MAUSOLEUM" --no-encryption --data-dir "$DATA_DIR_M7M" \
        >"$LOG_DIR/m-serial.log" 2>&1 &
    record_pid "$!"
    wait_ready "$PORT_MAUSOLEUM" 8
    "$BUILD_DIR/mausoleum/build/debug/wiki-seed" \
        --port "$PORT_MAUSOLEUM" --no-encryption --seed \
        >"$LOG_DIR/wiki-seed.log" 2>&1
    sleep 1

    echo "[bench] starting zeus + nexus (mausoleum-backed) on $SOCK_PROXY_DB" >&2
    "$BUILD_DIR/zeus/build/debug/zeus" -f -v -w "$WORKERS" -m 1048576 -s "$SOCK_PROXY_DB" \
        "$BUILD_DIR/nexus/build/debug/nexus" \
        >"$LOG_DIR/z-db.log" 2>&1 &
    record_pid "$!"
    wait_ready "$SOCK_PROXY_DB" 8

    echo "[bench] starting valet-proxy-db on :$PORT_PROXY_DB" >&2
    "$BUILD_DIR/valet/build/debug/valet" \
        -p "$PORT_PROXY_DB" --zeus-socket "$SOCK_PROXY_DB" \
        >"$LOG_DIR/v-db.log" 2>&1 &
    record_pid "$!"
    wait_ready "$PORT_PROXY_DB" 5
fi

# ────────────────────────────────────────────────────────────────────
# Run the matrix
# ────────────────────────────────────────────────────────────────────

echo "[bench] running wrk: -t$THREADS -c$CONNS -d${DURATION}s, zeus -w $WORKERS" >&2

results_file=$(mktemp /tmp/bench-results-XXXXXX.txt)
{
    run_wrk A "Valet direct, GET /"                       "http://127.0.0.1:$PORT_DIRECT/"
    run_wrk B "Valet direct, GET /json"                   "http://127.0.0.1:$PORT_DIRECT/json"
    run_wrk C "Valet direct, GET /static/test.html"       "http://127.0.0.1:$PORT_STATIC/static/test.html"

    if [[ "$SKIP" != *proxy* ]]; then
        run_wrk D "Valet → zeus → nexus, GET /"            "http://127.0.0.1:$PORT_PROXY/"
        run_wrk E "Valet → zeus → nexus, /wiki/welcome"   "http://127.0.0.1:$PORT_PROXY/wiki/welcome"
    fi

    if [[ "$SKIP" != *mausoleum* ]] && [[ "$SKIP" != *proxy* ]]; then
        run_wrk F "Valet → zeus → nexus → mausoleum, /wiki/welcome" \
                  "http://127.0.0.1:$PORT_PROXY_DB/wiki/welcome"
    fi
} | tee "$results_file"

# ────────────────────────────────────────────────────────────────────
# Render Markdown table
# ────────────────────────────────────────────────────────────────────

echo
echo "## Benchmark — wrk -t$THREADS -c$CONNS -d${DURATION}s, zeus -w $WORKERS, debug build"
echo
echo "| # | Path | req/s | p50 (ms) | p75 (ms) | p90 (ms) | p99 (ms) |"
echo "|---|---|---:|---:|---:|---:|---:|"

while IFS= read -r line; do
    [[ "$line" == RESULT* ]] || continue
    eval "$(echo "$line" | sed 's/^RESULT //')"
    printf "| **%s** | %s | %s | %s | %s | %s | %s |\n" \
        "$id" "$name" "$rps" "$p50" "$p75" "$p90" "$p99"
done < "$results_file"

# Optional JSON
if [[ -n "$JSON_OUT" ]]; then
    {
        echo "{"
        echo "  \"settings\": {"
        echo "    \"threads\": $THREADS, \"conns\": $CONNS,"
        echo "    \"duration_secs\": $DURATION, \"zeus_workers\": $WORKERS"
        echo "  },"
        echo "  \"results\": ["
        first=1
        while IFS= read -r line; do
            [[ "$line" == RESULT* ]] || continue
            eval "$(echo "$line" | sed 's/^RESULT //')"
            [[ $first -eq 1 ]] || echo ","
            first=0
            printf '    {"id": "%s", "name": %s, "rps": %s, "p50_ms": %s, "p75_ms": %s, "p90_ms": %s, "p99_ms": %s}' \
                "$id" "$(printf '%s' "$name" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')" "$rps" "$p50" "$p75" "$p90" "$p99"
        done < "$results_file"
        echo
        echo "  ]"
        echo "}"
    } > "$JSON_OUT"
    echo "[bench] JSON written to $JSON_OUT" >&2
fi

rm -f "$results_file"
