#!/bin/sh
# The scripted language servers' common part (test/test_lsp_server.ritz,
# test/test_lsp_editor.ritz). A test copies this, then one of the other
# scripts here, into a directory of its own as server.sh.
#
#   read_msg      read one frame; its body goes to $D/msg.$n (n counts from 1)
#   send BODY     write BODY as a frame (ASCII bodies: dash's ${#} counts bytes)
#   version       the "version" in the last message read
#   wait_for F    wait until the test creates $D/F
D=$(dirname "$0")
cr=$(printf '\r')
n=0
read_msg() {
  len=0
  while IFS= read -r line; do
    line=${line%"$cr"}
    [ -z "$line" ] && break
    case $line in Content-Length:*) len=${line#Content-Length: } ;; esac
  done
  [ "$len" -gt 0 ] 2>/dev/null || exit 0
  n=$((n+1))
  head -c "$len" > "$D/msg.$n"
}
send() { printf 'Content-Length: %d\r\n\r\n%s' "${#1}" "$1"; }
version() { sed -n 's/.*"version":\([0-9]*\).*/\1/p' "$D/msg.$n" | head -n 1; }
wait_for() { while [ ! -e "$D/$1" ]; do sleep 0.01; done; }
CAPS='{"jsonrpc":"2.0","id":1,"result":{"capabilities":{"textDocumentSync":1,"hoverProvider":true,"definitionProvider":true}}}'
