#!/bin/bash
# ritz-lsp: what it advertises, it answers (AGAST #2460, #2789).
#
# - The command line answers before the server starts (AGAST #3159).
# - initialize advertises textDocumentSync, hoverProvider and
#   definitionProvider, and nothing it cannot do: an unimplemented request
#   (completion) gets MethodNotFound (-32601), not a fake empty answer.
# - hover / definition on a function name in the open document answer with
#   its signature / its declaration; on anything else they answer null.
# - didOpen / didChange publish diagnostics from a ritz1 compile of the
#   buffer (#2789). A stub ritz1 (via $RITZ1) pins how its stderr becomes
#   diagnostics; the real ritz1, when it is built, pins the end-to-end
#   answer and the default lookup next to the monorepo's ritz1.
set -u
cd "$(dirname "$0")"
BIN=build/debug/ritz-lsp
[ -x "$BIN" ] || { echo "FAIL: $BIN not built"; exit 1; }
exec python3 -I - "$BIN" <<'PY'
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

BIN = os.path.abspath(sys.argv[1])
REAL_RITZ1 = Path(BIN).parents[2].parent / "ritz" / "ritz1" / "build" / "ritz1"

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
        p = subprocess.Popen([BIN, *args], stdin=r,
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

def session(msgs, argv=(), env=None, cwd=None):
    """Run one server over `msgs` (initialize first, shutdown/exit last);
    return (exit code, every message it sent, in order)."""
    msgs = ([{"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"processId": None, "rootUri": None, "capabilities": {}}},
             {"jsonrpc": "2.0", "method": "initialized", "params": {}}]
            + msgs
            + [{"jsonrpc": "2.0", "id": 99, "method": "shutdown"},
               {"jsonrpc": "2.0", "method": "exit"}])
    p = subprocess.run([BIN, *argv], input=b"".join(map(frame, msgs)),
                       capture_output=True, timeout=20, env=env, cwd=cwd)
    out = []
    for m in re.finditer(rb"Content-Length: (\d+)\r\n\r\n", p.stdout):
        out.append(json.loads(p.stdout[m.end():m.end() + int(m.group(1))]))
    return p.returncode, out

def by_id(out):
    return {m["id"]: m for m in out if "id" in m}

def diags(out):
    return [m["params"] for m in out if m.get("method") == "textDocument/publishDiagnostics"]

def did_open(uri, text, version=1):
    return {"jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": uri, "languageId": "ritz",
                                        "version": version, "text": text}}}

def did_change(uri, text, version):
    return {"jsonrpc": "2.0", "method": "textDocument/didChange",
            "params": {"textDocument": {"uri": uri, "version": version},
                       "contentChanges": [{"text": text}]}}

def req(rid, method, uri, line, ch):
    return {"jsonrpc": "2.0", "id": rid, "method": method,
            "params": {"textDocument": {"uri": uri},
                       "position": {"line": line, "character": ch}}}

def rng(l0, c0, l1, c1):
    return {"start": {"line": l0, "character": c0}, "end": {"line": l1, "character": c1}}

scratch = Path(tempfile.mkdtemp(prefix="ritz-lsp-test-"))
# Hover/definition never need ritz1; point it at nothing so these sessions
# don't depend on whether it is built.
NO_RITZ1 = {**os.environ, "RITZ1": str(scratch / "no-such-ritz1")}

# --- capabilities, hover, definition ---------------------------------------
uri = "file:///tmp/t2789.ritz"
src = ("# fn ghost() calls helper, in a comment\n"  # 0
       "fn helper() -> i32\n"                         # 1
       "    42\n"                                     # 2
       "\n"                                           # 3
       "pub fn main() -> i32\n"                       # 4
       "    let s: *u8 = c\"helper() fn spook()\"\n" # 5
       "    helper() + later<i32>(1) + ghost()\n"     # 6
       "\n"                                           # 7
       "pub fn later<T>(x: T) -> T\n"                 # 8
       "    x\n")                                     # 9
reqs = [
    req(2, "textDocument/hover", uri, 6, 6),          # helper( -> its signature
    req(3, "textDocument/definition", uri, 6, 6),     # helper( -> line 1
    req(4, "textDocument/definition", uri, 6, 17),    # later< (declared after use)
    req(5, "textDocument/hover", uri, 6, 15),         # later -> generic signature
    req(6, "textDocument/definition", uri, 6, 33),    # ghost: only in a comment
    req(7, "textDocument/hover", uri, 6, 33),
    req(8, "textDocument/definition", uri, 5, 8),     # `s`, not a function
    req(9, "textDocument/hover", uri, 3, 0),          # empty line
    req(10, "textDocument/definition", uri, 1, 5),    # the declaration itself
    req(11, "textDocument/hover", uri, 6, 10),        # just past `helper`: `(`
    req(12, "textDocument/definition", "file:///tmp/not-open.ritz", 0, 0),
    req(13, "textDocument/completion", uri, 6, 6),    # not implemented
    req(14, "textDocument/hover", uri, 0, 20),        # helper, in a comment
    req(15, "textDocument/definition", uri, 5, 20),   # helper, in a string
]
for argv in ([], ["--stdio"]):
    tag = " ".join(["ritz-lsp", *argv]) + ": "
    rc, out = session([did_open(uri, src), *reqs], argv, env=NO_RITZ1)
    r = by_id(out)
    caps = r.get(1, {}).get("result", {}).get("capabilities")
    check(tag + "initialize answered", caps is not None, repr(r.get(1)))
    caps = caps or {}
    check(tag + "textDocumentSync advertised", caps.get("textDocumentSync") == 1, repr(caps))
    check(tag + "hoverProvider advertised", caps.get("hoverProvider") is True, repr(caps))
    check(tag + "definitionProvider advertised", caps.get("definitionProvider") is True, repr(caps))
    check(tag + "completion not advertised", "completionProvider" not in caps, repr(caps))
    check(tag + "completion -> MethodNotFound",
          r.get(13, {}).get("error", {}).get("code") == -32601, repr(r.get(13)))
    check(tag + "shutdown answered", 99 in r, repr(sorted(r)))
    check(tag + "clean exit", rc == 0, f"exit {rc}")
    if argv:
        continue  # the answers below don't depend on argv

    h = r.get(2, {}).get("result") or {}
    check("hover helper -> markdown signature",
          h.get("contents") == {"kind": "markdown", "value": "```ritz\nfn helper() -> i32\n```"},
          repr(r.get(2)))
    check("hover helper -> range of the name", h.get("range") == rng(6, 4, 6, 10), repr(h))
    check("definition helper -> its declaration",
          r.get(3, {}).get("result") == {"uri": uri, "range": rng(1, 3, 1, 9)}, repr(r.get(3)))
    check("definition of a fn declared after the call",
          r.get(4, {}).get("result") == {"uri": uri, "range": rng(8, 7, 8, 12)}, repr(r.get(4)))
    h = r.get(5, {}).get("result") or {}
    check("hover generic fn -> its signature",
          h.get("contents", {}).get("value") == "```ritz\npub fn later<T>(x: T) -> T\n```", repr(r.get(5)))
    for rid, what in ((6, "definition of a name declared only in a comment"),
                      (7, "hover on a name declared only in a comment"),
                      (8, "definition of a local, not a fn"),
                      (9, "hover on an empty line"),
                      (11, "hover just past the name"),
                      (12, "definition in a document that is not open"),
                      (14, "hover on a fn name inside a comment"),
                      (15, "definition of a fn name inside a string")):
        check(what + " -> null", rid in r and "error" not in r[rid] and r[rid].get("result") is None,
              repr(r.get(rid)))
    check("definition on the declaration -> itself",
          r.get(10, {}).get("result") == {"uri": uri, "range": rng(1, 3, 1, 9)}, repr(r.get(10)))
    d = diags(out)
    check("ritz1 missing -> one warning, not an error",
          len(d) == 1 and len(d[0]["diagnostics"]) == 1
          and d[0]["diagnostics"][0]["severity"] == 2
          and "ritz1" in d[0]["diagnostics"][0]["message"], repr(d))

# --- diagnostics from a stub ritz1 -----------------------------------------
# The stub prints, to stderr, every `#! <line>` in its input with {in}
# replaced by the input path it was given, and exits with the code on a
# `#exit <n>` line (default 0). It records its argv and the input's text.
log = scratch / "stub.log"
stub = scratch / "ritz1"
stub.write_text(f"""#!{sys.executable} -I
import json, re, sys
argv = sys.argv[1:]
text = open(argv[0]).read()
with open({str(log)!r}, "a") as f:
    f.write(json.dumps({{"argv": argv, "text": text}}) + "\\n")
for m in re.finditer(r"(?m)^#! (.*)$", text):
    sys.stderr.write(m.group(1).replace("{{in}}", argv[0]) + "\\n")
m = re.search(r"(?m)^#exit (\\d+)$", text)
sys.exit(int(m.group(1)) if m else 0)
""")
stub.chmod(0o755)
STUB = {**os.environ, "RITZ1": str(stub)}

docdir = scratch / "proj"
docdir.mkdir()
duri = (docdir / "d.ritz").as_uri()
bad = ("#! {in}:2:5: error: Unknown function: nope\n"
       "    nope(1)\n"
       "#exit 1\n")
mixed = ("#! {in}:1:1: error: first\n"
         "#! note: {in}:1:1: a note on an error, not a diagnostic\n"
         "#! /elsewhere/other.ritz:3:7: error: in an import\n"
         "#! error: ritz1 cannot emit: unknown identifier 'y'\n"
         "#! {in}:9:2: error: \"quoted\" \\ msg\n"
         "#exit 1\n")
silent_fail = "#exit 3\n"
rc, out = session([did_open(duri, bad, 1), did_change(duri, "fn main() -> i32\n    0\n", 2),
                   did_change(duri, mixed, 3), did_change(duri, silent_fail, 4),
                   {"jsonrpc": "2.0", "method": "textDocument/didClose",
                    "params": {"textDocument": {"uri": duri}}}], env=STUB)
d = diags(out)
check("stub: didClose clears the document's diagnostics",
      d[-1:] == [{"uri": duri, "diagnostics": []}], repr(d[-1:]))
d = d[:-1]
check("stub: one publishDiagnostics per open/change", len(d) == 4, repr(d))
check("stub: diagnostics name the document's uri", d and all(x.get("uri") == duri for x in d), repr(d))
check("stub: diagnostics carry the document version",
      [x.get("version") for x in d] == [1, 2, 3, 4], repr([x.get("version") for x in d]))
d += [{}] * 4
check("stub: located error -> 0-based range over the name",
      d[0].get("diagnostics") == [{"range": rng(1, 4, 1, 8), "severity": 1, "source": "ritz1",
                                   "message": "Unknown function: nope"}], repr(d[0]))
check("stub: a clean compile clears the diagnostics", d[1].get("diagnostics") == [], repr(d[1]))
got = d[2].get("diagnostics") or []
check("stub: notes are not diagnostics", len(got) == 4, repr(got))
got += [{}] * 4
check("stub: located error at column 1",
      got[0].get("range") == rng(0, 0, 0, 1) and got[0].get("message") == "first", repr(got[0]))
check("stub: an error in another file -> line 0, located in the message",
      got[1].get("range") == rng(0, 0, 0, 0)
      and got[1].get("message") == "/elsewhere/other.ritz:3:7: error: in an import", repr(got[1]))
check("stub: an unlocated error -> line 0",
      got[2].get("range") == rng(0, 0, 0, 0)
      and got[2].get("message") == "error: ritz1 cannot emit: unknown identifier 'y'", repr(got[2]))
check("stub: a line past the end of the buffer keeps its position, message escaped",
      got[3].get("range", {}).get("start") == {"line": 8, "character": 1}
      and got[3].get("message") == "\"quoted\" \\ msg", repr(got[3]))
fail = d[3].get("diagnostics") or [{}]
check("stub: a failed compile with no error line -> one diagnostic naming the exit",
      len(fail) == 1 and fail[0].get("severity") == 1 and "exit 3" in fail[0].get("message", ""),
      repr(d[3]))
check("stub: clean exit", rc == 0, f"exit {rc}")

calls = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
check("stub: ritz1 ran once per open/change", len(calls) == 4, repr(calls))
calls += [{"argv": [""], "text": ""}] * 4
first = calls[0]["argv"]
check("stub: ritz1 compiles the buffer, not the file on disk", calls[0]["text"] == bad, repr(calls[0]))
check("stub: the input keeps the document's file name", os.path.basename(first[0]) == "d.ritz", repr(first))
check("stub: the input is a scratch copy, removed afterwards",
      not first[0].startswith(str(docdir)) and not os.path.exists(first[0])
      and not os.path.exists(os.path.dirname(first[0])), repr(first))
check("stub: -o goes to a scratch file", len(first) >= 3 and first[1] == "-o"
      and not first[2].startswith(str(docdir)), repr(first))
check("stub: -I puts the document's directory on the import path",
      "-I" in first and str(docdir) in first[first.index("-I") + 1].split(":")[0], repr(first))
check("stub: nothing written next to the document", sorted(os.listdir(docdir)) == [], repr(os.listdir(docdir)))

# --- diagnostics from the real ritz1 ----------------------------------------
if REAL_RITZ1.is_file():
    env = {k: v for k, v in os.environ.items() if k not in ("RITZ1", "RITZ_PATH")}
    ruri = (docdir / "real.ritz").as_uri()
    undefined = "fn main() -> i32\n    nope(1)\n"
    uses_ritzlib = 'import ritzlib.io\n\nfn main() -> i32\n    prints_cstr(c"hi\\n")\n    0\n'
    rc, out = session([did_open(ruri, undefined, 1), did_change(ruri, uses_ritzlib, 2)],
                      env=env, cwd=str(scratch))
    d = diags(out) + [{}, {}]
    got = d[0].get("diagnostics") or [{}]
    check("ritz1: a call to an undefined fn is an error at the call",
          len(got) == 1 and got[0].get("range") == rng(1, 4, 1, 8) and got[0].get("severity") == 1
          and "nope" in got[0].get("message", ""), repr(d[0]))
    check("ritz1: ritzlib imports resolve with no RITZ_PATH set",
          d[1].get("diagnostics") == [], repr(d[1]))
else:
    print(f"skip: real ritz1 not built ({REAL_RITZ1}); make -C projects/ritz ritz1")

shutil.rmtree(scratch, ignore_errors=True)
if fails:
    print(f"{len(fails)} ritz-lsp check(s) failed")
    sys.exit(1)
PY
