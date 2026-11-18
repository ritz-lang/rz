# lib_ports.sh - free TCP ports for valet shell tests (AGAST #3685, #3694)
#
# Source it:  . "$(dirname "${BASH_SOURCE[0]}")/lib_ports.sh"
#
# valet sets SO_REUSEPORT, so a second valet on the same port binds without
# error and the kernel splits connections between the two. With fixed ports a
# gate's client once finished its handshake with a room's mutated valet on the
# same port (#3685). Two copies of a test at once, in two gate slots or a gate
# and a room's by-hand run, must never share a port, so each run picks random
# unused ones below the kernel's ephemeral range (32768 on), where no client
# socket's local port can be. A port given by hand (PORT=...) is still
# honoured, but one that already has a listener is refused, not shared.
#
#   PORT="${PORT:-$(pick_port)}"
#   SPORT="${SPORT:-$(pick_port "$PORT")}"   # never equal to $PORT
#   require_free_port "$PORT" "$SPORT" || exit 1
#
# Pinned by projects/ritz/tools/test_valet_test_ports.py.

# True if something on 127.0.0.1 accepts a connection on port $1.
port_taken() {
    (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

# Print a random port in 10000..31999 with no listener, other than any of
# the ports given as arguments.
pick_port() {
    local p a ok
    while :; do
        p=$((10000 + RANDOM % 22000))
        ok=1
        for a in "$@"; do
            [ "$p" = "$a" ] && ok=
        done
        [ -n "$ok" ] && ! port_taken "$p" && break
    done
    echo "$p"
}

# Fail (status 1, naming the port) if any port given already has a listener.
require_free_port() {
    local p
    for p in "$@"; do
        if port_taken "$p"; then
            echo "FAIL: port $p already has a listener; valet's SO_REUSEPORT would share it"
            return 1
        fi
    done
}
