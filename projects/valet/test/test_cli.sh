#!/bin/bash
# test_cli.sh - valet's command line (ritzlib.argspec, AGAST #1495)
#
# Tests:
#   - A non-numeric --port / --workers value is a usage error, not a silent 0
#     (which used to fall back to the config port and start the server)
#   - An unknown option and an option missing its value are usage errors
#   - --help lists every option and exits 0
#   - --config and --zeus-socket hand their path through (both fail cleanly
#     on a path that does not exist, after naming it)
#   - --port=N with -w/-m starts the server and serves /hello
#
# Usage: bash projects/valet/test/test_cli.sh  (after ./rz build valet)
#
# Exit only 0 or 1 (see test_tls_socket.sh).

VALET="${VALET:-$(dirname "$0")/../build/debug/valet}"
VALET="$(cd "$(dirname "$VALET")" && pwd)/$(basename "$VALET")"
PORT="${PORT:-9190}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

FAILED=0
SERVER_PID=""
# Run from an empty directory so no stray valet.json is picked up.
WORK="$(mktemp -d)"

pass() {
    echo -e "${GREEN}PASS${NC}: $1"
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    FAILED=1
}

cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -9 "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -rf "$WORK"
}
trap cleanup EXIT

if [ ! -x "$VALET" ]; then
    echo -e "${RED}ERROR${NC}: valet binary not found: $VALET"
    exit 1
fi

# run_valet ARGS... : run valet briefly (a server that starts is killed by
# the timeout: status 124) and leave its status, stdout and stderr in
# RC, OUT and ERR.
run_valet() {
    (cd "$WORK" && timeout 3 "$VALET" "$@" >"$WORK/out" 2>"$WORK/err")
    RC=$?
    OUT="$(cat "$WORK/out")"
    ERR="$(cat "$WORK/err")"
}

# expect_usage_error NAME STDERR_SUBSTRING ARGS...
expect_usage_error() {
    local name=$1 want=$2
    shift 2
    run_valet "$@"
    if [ "$RC" -eq 1 ] && [[ "$ERR" == *"$want"* ]] && [[ "$OUT" != *"Valet HTTP Server"* ]]; then
        pass "$name"
    else
        fail "$name (status $RC, stderr: $ERR)"
    fi
}

echo "=== Usage errors ==="
expect_usage_error "-p abc is rejected" "valet: invalid number 'abc'" -p abc
expect_usage_error "--workers=2x is rejected" "valet: invalid number '2x'" --port 9191 --workers=2x
expect_usage_error "unknown option is rejected" "valet: unknown option '--bogus'" --bogus
expect_usage_error "-p without a value is rejected" "valet: option '-p' requires a value" -p

echo ""
echo "=== --help ==="
run_valet --help
HELP_OK=1
for opt in --help --config --port --workers --multishot --zeus-socket; do
    [[ "$OUT" == *"$opt"* ]] || HELP_OK=0
done
if [ "$RC" -eq 0 ] && [ "$HELP_OK" -eq 1 ]; then
    pass "--help lists every option and exits 0"
else
    fail "--help (status $RC): $OUT"
fi

echo ""
echo "=== Paths reach their consumers ==="
run_valet -c "$WORK/missing.json"
if [ "$RC" -eq 1 ] && [[ "$ERR" == *"failed to load config file"* ]]; then
    pass "-c PATH is loaded (and a missing file fails)"
else
    fail "-c PATH (status $RC, stderr: $ERR)"
fi

run_valet --port "$PORT" --zeus-socket="$WORK/no.sock"
if [ "$RC" -eq 1 ] && [[ "$OUT" == *"zeus socket: $WORK/no.sock"* ]] && [[ "$ERR" == *"zeus_client_connect failed"* ]]; then
    pass "--zeus-socket=PATH is connected to"
else
    fail "--zeus-socket=PATH (status $RC, stdout: $OUT, stderr: $ERR)"
fi

echo ""
echo "=== Valid flags start the server ==="
(cd "$WORK" && exec "$VALET" --port="$PORT" -w 1 -m >"$WORK/srv.out" 2>&1) &
SERVER_PID=$!
RESP=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.2
    RESP="$(curl -s --max-time 2 "http://localhost:$PORT/hello")" && [ -n "$RESP" ] && break
done
if [ "$RESP" = "Hello from Valet!" ]; then
    pass "--port=N -w 1 -m serves /hello"
else
    fail "--port=N -w 1 -m: got '$RESP'; server output: $(cat "$WORK/srv.out")"
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All CLI tests passed!${NC}"
    exit 0
fi
echo -e "${RED}Some CLI tests failed${NC}"
exit 1
