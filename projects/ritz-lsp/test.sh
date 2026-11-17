#!/bin/bash
# ritz-lsp must not advertise what it cannot do (AGAST #2460).
#
# The server does JSON-RPC transport and document sync. Hover and
# go-to-definition used to be advertised and answered `null` for every
# position; until #2789 implements them they must not be advertised, and a
# request for them gets MethodNotFound (-32601), not a fake empty answer.
#
# Its command line answers before the server starts (AGAST #3159).
set -u
cd "$(dirname "$0")"
BIN=build/debug/ritz-lsp
[ -x "$BIN" ] || { echo "FAIL: $BIN not built"; exit 1; }
exec python3 -I - "$BIN" <<'PY'
import json, os, re, subprocess, sys

fails = []
def check(name, ok, detail):
    print(("ok: " if ok else "FAIL: ") + name + ("" if ok else ": " + detail))
    if not ok:
        fails.append(name)

# Command line (#3159). -h/--help: usage on stdout, exit 0, before the server
# starts. Any other argument except --stdio: usage on stderr, exit 2, stdout
# untouched. stdin stays open (we hold the write end, as an editor would), so
# a server that starts anyway times out here instead of passing on EOF.
def cli(*args):
    r, w = os.pipe()
    try:
        p = subprocess.Popen([sys.argv[1], *args], stdin=r,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.close(r)
        try:
            out, err = p.communicate(timeout=5)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            p.kill()
            out, err = p.communicate()
            rc = "timeout (server started)"
    finally:
        os.close(w)
    return rc, out.decode(errors="replace"), err.decode(errors="replace")

for args in (["--help"], ["-h"]):
    rc, out, err = cli(*args)
    check(f"{args[0]} exits 0", rc == 0, f"exit {rc} (stderr {err[:80]!r})")
    check(f"{args[0]} prints usage on stdout", "Usage: ritz-lsp" in out, repr(out[:80]))
for args in (["--bogus"], ["foo"], ["--stdio", "--bogus"]):
    name = " ".join(args)
    rc, out, err = cli(*args)
    check(f"{name} is a usage error (exit 2)", rc == 2, f"exit {rc} (stderr {err[:80]!r})")
    check(f"{name} leaves stdout clean", out == "", repr(out[:80]))
    check(f"{name} prints usage on stderr", "Usage: ritz-lsp" in err, repr(err[:80]))

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

# No arguments, and --stdio (what editors' LSP clients pass), both serve.
for argv in ([], ["--stdio"]):
    tag = " ".join(["ritz-lsp", *argv]) + ": "
    p = subprocess.run([sys.argv[1], *argv], input=b"".join(map(frame, msgs)),
                       capture_output=True, timeout=10)
    replies = {}
    for m in re.finditer(rb"Content-Length: (\d+)\r\n\r\n", p.stdout):
        body = json.loads(p.stdout[m.end():m.end() + int(m.group(1))])
        if "id" in body:
            replies[body["id"]] = body

    caps = replies.get(1, {}).get("result", {}).get("capabilities")
    check(tag + "initialize answered", caps is not None, repr(replies.get(1)))
    caps = caps or {}
    check(tag + "textDocumentSync advertised", caps.get("textDocumentSync") == 1, repr(caps))
    for rid, cap, method in ((2, "hoverProvider", "hover"), (3, "definitionProvider", "definition")):
        check(tag + f"{cap} not advertised", not caps.get(cap), repr(caps))
        r = replies.get(rid, {})
        check(tag + f"{method} -> MethodNotFound", r.get("error", {}).get("code") == -32601, repr(r))
    check(tag + "shutdown answered", 4 in replies, repr(sorted(replies)))
    check(tag + "clean exit", p.returncode == 0, f"exit {p.returncode}")
if fails:
    print(f"{len(fails)} ritz-lsp check(s) failed")
    sys.exit(1)
PY
