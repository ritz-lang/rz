#!/usr/bin/env bash
# test/e2e_large_page.sh - valet -> zeus -> nexus with max-size pages (AGAST #2104)
#
# Starts zeus (bench settings: -w 1 -m 1048576) with nexus as the worker and
# valet in --zeus-socket mode, then checks over real HTTP:
#
#   1. POST of a max-size page (8192 raw `"`, body > valet's 8 KB read_buf)
#      succeeds with a 303 — the body is read whole and fits the zeus slot.
#   2. GET of that page returns 200 with the whole ~49 KB+ escaped body
#      (8192 `&quot;`), Content-Length matching what arrived, no hang.
#   3. The connection stays usable afterwards (keep-alive second request).
#   4. A request body bigger than a zeus slot gets a clean 4xx/5xx, never a
#      hang or a truncated 200.
#
# Needs debug builds of zeus, valet and nexus:
#   ./rz build zeus && ./rz build valet && ./rz build nexus
# Run from anywhere:  bash projects/nexus/test/e2e_large_page.sh
set -u

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
ZEUS="${ZEUS:-$ROOT/projects/zeus/build/debug/zeus}"
VALET="${VALET:-$ROOT/projects/valet/build/debug/valet}"
NEXUS="${NEXUS:-$ROOT/projects/nexus/build/debug/nexus}"

for b in "$ZEUS" "$VALET" "$NEXUS"; do
    if [[ ! -x "$b" ]]; then
        echo "FAIL: missing binary $b (build zeus, valet and nexus first)" >&2
        exit 1
    fi
done
command -v curl >/dev/null || { echo "FAIL: curl not found" >&2; exit 1; }

TMP="$(mktemp -d)"
SOCK="$TMP/zeus.sock"
PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')"
PIDS=()
cleanup() {
    for p in "${PIDS[@]}"; do kill -9 "$p" 2>/dev/null; done
    wait 2>/dev/null
    rm -rf "$TMP"
}
trap cleanup EXIT

FAILS=0
fail() { echo "FAIL: $*" >&2; FAILS=$((FAILS + 1)); }
pass() { echo "ok: $*"; }

# zeus execs the worker with cwd = ours; keep nexus's files in $TMP.
(cd "$TMP" && exec "$ZEUS" -f -w 1 -m 1048576 -s "$SOCK" -p "$TMP/zeus.pid" "$NEXUS") \
    >"$TMP/zeus.log" 2>&1 &
PIDS+=("$!")
for _ in $(seq 1 80); do [[ -S "$SOCK" ]] && break; sleep 0.1; done
[[ -S "$SOCK" ]] || { cat "$TMP/zeus.log" >&2; echo "FAIL: zeus socket never appeared" >&2; exit 1; }
sleep 0.5   # let the worker attach

(cd "$TMP" && exec "$VALET" -p "$PORT" --zeus-socket "$SOCK") >"$TMP/valet.log" 2>&1 &
PIDS+=("$!")
for _ in $(seq 1 80); do
    curl -s -o /dev/null --max-time 1 "http://127.0.0.1:$PORT/health" && break
    sleep 0.1
done

BASE="http://127.0.0.1:$PORT"

# --- 1. POST a max-size page --------------------------------------------------
python3 -c 'import sys; sys.stdout.write("slug=big&content=" + "\"" * 8192)' >"$TMP/post.body"
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-binary @"$TMP/post.body" "$BASE/wiki")"
if [[ "$code" == "303" ]]; then pass "POST max-size page -> 303"; else fail "POST max-size page -> '$code' (want 303)"; fi

# --- 2. GET it back whole -----------------------------------------------------
code="$(curl -s -D "$TMP/get.hdr" -o "$TMP/get.body" -w '%{http_code}' --max-time 10 "$BASE/wiki/big")"
rc=$?
got="$(stat -c %s "$TMP/get.body" 2>/dev/null || echo 0)"
clen="$(tr -d '\r' <"$TMP/get.hdr" | awk -F': ' 'tolower($1)=="content-length"{print $2}')"
quots="$(grep -o '&quot;' "$TMP/get.body" | wc -l)"
if [[ $rc -ne 0 ]]; then
    fail "GET /wiki/big: curl exit $rc (hang/timeout?), got $got bytes"
elif [[ "$code" != "200" ]]; then
    fail "GET /wiki/big -> $code (want 200)"
elif [[ "$got" -lt 49152 || "$got" != "$clen" ]]; then
    fail "GET /wiki/big: body $got bytes, Content-Length '$clen' (want >= 49152, equal)"
elif [[ "$quots" -ne 8192 ]]; then
    fail "GET /wiki/big: $quots &quot; (want 8192)"
else
    pass "GET max-size page -> 200, $got bytes, 8192 &quot;"
fi

# --- 3. Keep-alive: big response then a small one on the same connection ------
out="$(curl -s --max-time 10 -o /dev/null -w '%{http_code} %{num_connects}\n' \
    "$BASE/wiki/big" -o /dev/null "$BASE/health")"
if [[ "$(echo "$out" | awk 'NR==2{print $1}')" == "200" && "$(echo "$out" | awk 'NR==2{print $2}')" == "0" ]]; then
    pass "keep-alive after large response"
else
    fail "keep-alive after large response: '$(echo $out)' (want second '200 0')"
fi

# --- 4. Request body larger than a zeus slot: clean error, no hang ------------
python3 -c 'import sys; sys.stdout.write("slug=huge&content=" + "a" * 300000)' >"$TMP/huge.body"
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
    --data-binary @"$TMP/huge.body" "$BASE/wiki")"
rc=$?
if [[ $rc -eq 0 && "$code" =~ ^[45][0-9][0-9]$ ]]; then
    pass "oversize request -> $code"
else
    fail "oversize request -> '$code' curl exit $rc (want clean 4xx/5xx)"
fi

# valet must still be alive and serving.
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$BASE/health")"
[[ "$code" == "200" ]] && pass "valet still serving" || fail "valet not serving after tests ($code)"

if [[ $FAILS -ne 0 ]]; then
    echo "--- valet.log (tail)"; tail -20 "$TMP/valet.log"
    echo "--- zeus.log (tail)"; tail -20 "$TMP/zeus.log"
    echo "$FAILS check(s) failed"
    exit 1
fi
echo "all e2e checks passed"
