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
#   bench/run.sh --dry-run             # print ports, orphan check and what
#                                      # cleanup would kill; start nothing
#
# Ports default to free ones picked at start, so rooms sharing a host never
# collide.  Pin any of them with BENCH_PORT_DIRECT, BENCH_PORT_STATIC,
# BENCH_PORT_PROXY, BENCH_PORT_PROXY_DB or BENCH_PORT_MAUSOLEUM.
#
# Requires: wrk, curl, bash, the binaries built via `./rz build PROJECT`.

set -euo pipefail

# ────────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────────

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
BENCH_DIR="$REPO_ROOT/bench"
BUILD_DIR="$REPO_ROOT/projects"

DURATION=10
CONNS=100
THREADS=4
WORKERS=1                # zeus worker count for proxy scenarios
SKIP=""
JSON_OUT=""
KEEP=0                   # if 1, leave servers running on exit
DRY_RUN=0                # if 1, report ports / orphans / cleanup and exit

# Ports are picked after arg parsing (see "Ports" below): BENCH_PORT_* if
# set, else a free one, never a fixed number another room also uses
# (AGAST #3201).
PORT_NAMES=(PORT_DIRECT PORT_STATIC PORT_PROXY PORT_PROXY_DB PORT_MAUSOLEUM)

# The mausoleum data dir, logs and wrk output live in one `mktemp -d`, and
# the unix sockets in a second one, both removed by the EXIT trap (kept with
# --keep), so two rooms benching on one host never share a path (AGAST #3183).
# The socket dir comes from sock_dir: $TMPDIR if a socket path under it fits
# sun_path's 107 bytes (a gate's, deep in its worktree, does not: zeus's
# bind() fails, AGAST #4135), else $XDG_RUNTIME_DIR, else /tmp, moving on
# when a mktemp fails (a full /tmp, AGAST #4274/#4282).
. "$REPO_ROOT/projects/ritz/tools/sock_dir.sh"
T=$(mktemp -d)
SOCK_DIR=$(sock_dir rz_bench_sock. zeus_bench_inmem.sock) || { rm -rf "$T"; exit 1; }
trap 'rm -rf "$T" "$SOCK_DIR"' EXIT     # until cleanup() below takes over
SOCK_PROXY="$SOCK_DIR/zeus_bench_inmem.sock"
SOCK_PROXY_DB="$SOCK_DIR/zeus_bench_db.sock"

DATA_DIR_M7M="$T/m7m_bench_data"
LOG_DIR="$T/logs"
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
        --dry-run)  DRY_RUN=1;      shift   ;;
        -h|--help)
            sed -n '/^# Usage:/,/^# Requires:/p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

# ────────────────────────────────────────────────────────────────────
# Utilities
# ────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────
# Ports
# ────────────────────────────────────────────────────────────────────

# Free loopback ports from the kernel, one per line: all bound at once so
# they are distinct, then released for the servers to take.
free_ports() {
    python3 -c '
import socket, sys
socks = [socket.socket() for _ in range(int(sys.argv[1]))]
for s in socks:
    s.bind(("127.0.0.1", 0))
print("\n".join(str(s.getsockname()[1]) for s in socks))
' "$1"
}

mapfile -t _free < <(free_ports "${#PORT_NAMES[@]}")
for i in "${!PORT_NAMES[@]}"; do
    name="${PORT_NAMES[$i]}"
    override="BENCH_$name"
    port="${!override:-${_free[$i]}}"
    if ! [[ "$port" =~ ^[0-9]+$ ]] || (( port < 1 || port > 65535 )); then
        echo "[bench] $override must be a port number 1-65535, got '$port'" >&2
        exit 2
    fi
    printf -v "$name" '%s' "$port"
done

# ────────────────────────────────────────────────────────────────────
# Processes: what this run started, and nothing else (AGAST #3201)
# ────────────────────────────────────────────────────────────────────

PIDS=()
record_pid() { PIDS+=("$1"); }

# PID and all its descendants (zeus's nexus workers), one per line.
# Collected before anything is killed, while the tree is still linked.
pid_tree() {
    local pid
    for pid in "$@"; do
        echo "$pid"
        pid_tree $(ps -o pid= --ppid "$pid" 2>/dev/null)
    done
}

# PIDs whose executable is one of THIS worktree's bench servers.  Matched
# on /proc/PID/exe, the resolved binary, so it catches absolute and
# relative spawns alike, and never another worktree's server or a clang
# writing `-o .../build/...`.  Another user's processes are unreadable
# and so never listed.
# One find over /proc, not a readlink per process: hosts run thousands.
own_bench_pids() {
    find /proc -mindepth 2 -maxdepth 2 -name exe \( \
            -lname "$BUILD_DIR/valet/build/*" -o \
            -lname "$BUILD_DIR/nexus/build/*" -o \
            -lname "$BUILD_DIR/zeus/build/*" -o \
            -lname "$BUILD_DIR/mausoleum/build/*" \) \
            -printf '%h\n' 2>/dev/null \
        | sed -n 's|^/proc/\([0-9]*\)$|\1|p' || true
}

cleanup() {
    if [[ "$KEEP" == "1" ]]; then
        echo "[bench] --keep: leaving servers running. PIDs: ${PIDS[*]}" >&2
        echo "[bench] --keep: data and logs left in $T, sockets in $SOCK_DIR" >&2
        return
    fi
    # Only what this run started: the recorded PIDs and their children.
    # Never a pattern kill: other rooms on this host run the same
    # binaries from their own worktrees.
    local victims
    victims=$(pid_tree "${PIDS[@]}" | tr '\n' ' ')
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "[bench] dry-run: cleanup would kill:${victims:+ ${victims% }}" >&2
    else
        for pid in $victims; do
            kill -9 "$pid" 2>/dev/null || true
        done
    fi
    rm -rf "$T" "$SOCK_DIR"
}
trap cleanup EXIT

# ────────────────────────────────────────────────────────────────────
# Orphan guard — refuse to start if there are leftover bench binaries
# from earlier sessions still running.  These hold the bench ports and
# cause new `valet -p 9099` spawns to bind their own port without
# conflict (SO_REUSEPORT), so requests get serviced by the OLD valet
# with stale code.  This silently invalidates every measurement until
# someone manually finds and kills them.  Refuse to start so the user
# notices.
# ────────────────────────────────────────────────────────────────────

# Scoped to this worktree's binaries (own_bench_pids): another room's
# servers hold their own ports and never answer ours, so they are not
# orphans of this run and must not block it.
orphan_pids=$(own_bench_pids | tr '\n' ' ')
orphan_pids="${orphan_pids% }"
if [[ -n "$orphan_pids" ]]; then
    echo "[bench] ABORT: this worktree's bench binaries still running (pids: $orphan_pids)" >&2
    echo "[bench]        check they are yours, then:  kill -9 $orphan_pids" >&2
    exit 1
fi

if [[ "$DRY_RUN" == "1" ]]; then
    for name in "${PORT_NAMES[@]}"; do
        echo "[bench] dry-run: port $name=${!name}" >&2
    done
    echo "[bench] dry-run: socket SOCK_PROXY=$SOCK_PROXY" >&2
    echo "[bench] dry-run: socket SOCK_PROXY_DB=$SOCK_PROXY_DB" >&2
    echo "[bench] dry-run: no orphaned bench binaries under $BUILD_DIR" >&2
    exit 0
fi

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
    log=$(mktemp "$T/wrk.XXXXXX")
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

results_file="$T/results.txt"
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

