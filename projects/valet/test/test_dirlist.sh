#!/bin/bash
# Test directory listing

# A free port, never a fixed one: valet's SO_REUSEPORT would share it (#3694).
. "$(dirname "${BASH_SOURCE[0]}")/lib_ports.sh"
PORT="${PORT:-$(pick_port)}"
require_free_port "$PORT" || exit 1
cd "$(dirname "$0")/.."

# Start server in background (using unique port to avoid conflicts)
./valet -p $PORT &
VALET_PID=$!
sleep 1

# Test directory listing
echo "Testing directory listing at /static/..."
printf "GET /static/ HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" | nc -q 1 localhost $PORT

# Cleanup
kill $VALET_PID 2>/dev/null
exit 0
