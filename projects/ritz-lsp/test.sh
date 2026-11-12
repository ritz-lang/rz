#!/bin/bash
# ritz-lsp must not advertise what it cannot do (AGAST #2460).
#
# The server does JSON-RPC transport and document sync. Hover and
# go-to-definition used to be advertised and answered `null` for every
# position; until #2789 implements them they must not be advertised, and a
# request for them gets MethodNotFound (-32601), not a fake empty answer.
set -u
cd "$(dirname "$0")"
BIN=build/debug/ritz-lsp
[ -x "$BIN" ] || { echo "FAIL: $BIN not built"; exit 1; }
exec python3 -I - "$BIN" <<'PY'
import json, re, subprocess, sys

def frame(obj):
    b = json.dumps(obj).encode()
    return b"Content-Length: %d\r\n\r\n%s" % (len(b), b)

uri = "file:///tmp/t2460.ritz"
pos = {"textDocument": {"uri": uri}, "position": {"line": 4, "character": 6}}
msgs = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"processId": None, "rootUri": None, "capabilities": {}}},
    {"jsonrpc": "2.0", "method": "initialized", "params": {}},
    {"jsonrpc": "2.0", "method": "textDocument/didOpen",
     "params": {"textDocument": {"uri": uri, "languageId": "ritz", "version": 1,
                                 "text": "fn helper() -> i32\n    42\n\nfn main() -> i32\n    helper()\n"}}},
    {"jsonrpc": "2.0", "id": 2, "method": "textDocument/hover", "params": pos},
    {"jsonrpc": "2.0", "id": 3, "method": "textDocument/definition", "params": pos},
    {"jsonrpc": "2.0", "id": 4, "method": "shutdown"},
    {"jsonrpc": "2.0", "method": "exit"},
]
p = subprocess.run([sys.argv[1]], input=b"".join(map(frame, msgs)),
                   capture_output=True, timeout=10)
replies = {}
for m in re.finditer(rb"Content-Length: (\d+)\r\n\r\n", p.stdout):
    body = json.loads(p.stdout[m.end():m.end() + int(m.group(1))])
    if "id" in body:
        replies[body["id"]] = body

fails = []
def check(name, ok, detail):
    print(("ok: " if ok else "FAIL: ") + name + ("" if ok else ": " + detail))
    if not ok:
        fails.append(name)

caps = replies.get(1, {}).get("result", {}).get("capabilities")
check("initialize answered", caps is not None, repr(replies.get(1)))
caps = caps or {}
check("textDocumentSync advertised", caps.get("textDocumentSync") == 1, repr(caps))
for rid, cap, method in ((2, "hoverProvider", "hover"), (3, "definitionProvider", "definition")):
    check(f"{cap} not advertised", not caps.get(cap), repr(caps))
    r = replies.get(rid, {})
    check(f"{method} -> MethodNotFound", r.get("error", {}).get("code") == -32601, repr(r))
check("shutdown answered", 4 in replies, repr(sorted(replies)))
check("clean exit", p.returncode == 0, f"exit {p.returncode}")
if fails:
    print(f"{len(fails)} ritz-lsp check(s) failed")
    sys.exit(1)
PY
