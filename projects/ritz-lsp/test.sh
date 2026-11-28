#!/bin/bash
# ritz-lsp: what it advertises, it answers (AGAST #2460, #2789).
#
# - The command line answers before the server starts (AGAST #3159).
# - initialize advertises textDocumentSync, hoverProvider and
#   definitionProvider, and nothing it cannot do: an unimplemented request
#   (completion) gets MethodNotFound (-32601), not a fake empty answer.
# - hover / definition on a function name in the open document answer with
#   its signature / its declaration; on anything else they answer null.
# - ... and on a function the document imports, the same from the imported
#   file, resolved as ritz1 resolves it, exported names only (#3884).
# - didOpen / didChange publish diagnostics from a ritz1 compile of the
#   buffer (#2789), once input pauses: a burst of changes the server has not
#   yet read compiles once and publishes the last version only (#3902). A stub ritz1 (via $RITZ1) pins how its stderr becomes
#   diagnostics; the real ritz1, when it is built, pins the end-to-end
#   answer and the default lookup next to the monorepo's ritz1.
# - A ritz1 that hangs is killed at the deadline, reaped, reported as one
#   "timed out" warning, and the server goes on answering (#3883).
# - Positions are UTF-16 code units both ways: hover, definition and a
#   diagnostic after é, € and 😀 (a surrogate pair) on the same line (#3885).
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
    # Raw UTF-8, as most editors send it.
    b = json.dumps(obj, ensure_ascii=False).encode()
    return b"Content-Length: %d\r\n\r\n%s" % (len(b), b)

def frame_escaped(obj):
    # Non-ASCII as \uXXXX escapes, a surrogate pair for U+10000 and up: what
    # json.dumps sends by default, as some clients do (#3914).
    b = json.dumps(obj, ensure_ascii=True).encode()
    return b"Content-Length: %d\r\n\r\n%s" % (len(b), b)

def session(msgs, argv=(), env=None, cwd=None, framer=frame):
    """Run one server over `msgs` (initialize first, shutdown/exit last);
    return (exit code, every message it sent, in order)."""
    msgs = ([{"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"processId": None, "rootUri": None, "capabilities": {}}},
             {"jsonrpc": "2.0", "method": "initialized", "params": {}}]
            + msgs
            + [{"jsonrpc": "2.0", "id": 99, "method": "shutdown"},
               {"jsonrpc": "2.0", "method": "exit"}])
    p = subprocess.run([BIN, *argv], input=b"".join(map(framer, msgs)),
                       capture_output=True, timeout=20, env=env, cwd=cwd)
    out = []
    for m in re.finditer(rb"Content-Length: (\d+)\r\n\r\n", p.stdout):
        out.append(json.loads(p.stdout[m.end():m.end() + int(m.group(1))]))
    return p.returncode, out

# Content-Length is read by ritzlib's strview_parse_i64 (#1958): digits only,
# range-checked. A value that is not a positive length the server can buffer
# closes the connection unanswered; the hand-written loop it replaced wrapped
# 2^64 + n round to n and read "<n>x" as n, answering a frame it should not.
INIT = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"processId": None, "rootUri": None,
                              "capabilities": {}}}).encode()
def raw_init(value):
    """initialize under a hand-written Content-Length value; return
    (exit code, ids of the responses it sent)."""
    stdin = (b"Content-Length: " + value + b"\r\n\r\n" + INIT
             + frame({"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
             + frame({"jsonrpc": "2.0", "method": "exit"}))
    p = subprocess.run([BIN], input=stdin, capture_output=True, timeout=20)
    ids = [json.loads(p.stdout[m.end():m.end() + int(m.group(1))]).get("id")
           for m in re.finditer(rb"Content-Length: (\d+)\r\n\r\n", p.stdout)]
    return p.returncode, ids
n = len(INIT)
for label, value, answered in (
        ("the exact length", b"%d" % n, True),
        ("the exact length, padded", b"  %d \t" % n, True),
        ("0", b"0", False),
        ("i64::MIN", b"-9223372036854775808", False),
        ("i64::MAX", b"9223372036854775807", False),
        ("i64::MAX + 1", b"9223372036854775808", False),
        ("2^64 + the length (wraps to it)", b"%d" % (2**64 + n), False),
        ("the length with trailing junk", b"%dx" % n, False),
        ("a signed length", b"+%d" % n, False),
        ("a non-digit", b"abc", False)):
    rc, ids = raw_init(value)
    check(f"Content-Length {label}: {'answered' if answered else 'closes unanswered'}",
          rc == 0 and ((1 in ids) == answered), f"exit {rc}, answered ids {ids}")

class Live:
    """A server driven one step at a time. `first` is written into its stdin
    pipe before it starts, so it reads all of `first` as one burst."""
    def __init__(self, first, env, cwd=None):
        r, w = os.pipe()
        os.write(w, b"".join(map(frame, first)))  # well under the pipe's 64K
        self.p = subprocess.Popen([BIN], stdin=r, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, env=env, cwd=cwd)
        os.close(r)
        self.w, self.buf, self.out = w, b"", []

    def send(self, *msgs):
        os.write(self.w, b"".join(map(frame, msgs)))

    def until(self, pred, timeout=15):
        """Read messages until one satisfies pred; return it (None on timeout)."""
        import select, time
        end = time.monotonic() + timeout
        while True:
            while (m := re.search(rb"Content-Length: (\d+)\r\n\r\n", self.buf)) \
                    and len(self.buf) >= m.end() + int(m.group(1)):
                msg = json.loads(self.buf[m.end():m.end() + int(m.group(1))])
                self.buf = self.buf[m.end() + int(m.group(1)):]
                self.out.append(msg)
                if pred(msg):
                    return msg
            left = end - time.monotonic()
            if left <= 0 or not select.select([self.p.stdout], [], [], left)[0]:
                return None
            chunk = os.read(self.p.stdout.fileno(), 65536)
            if not chunk:
                return None
            self.buf += chunk

    def publish(self, timeout=15):
        return self.until(lambda m: m.get("method") == "textDocument/publishDiagnostics", timeout)

    def finish(self):
        """shutdown + exit; return the exit code (None if it did not exit)."""
        self.send({"jsonrpc": "2.0", "id": 99, "method": "shutdown"},
                  {"jsonrpc": "2.0", "method": "exit"})
        self.until(lambda m: m.get("id") == 99)
        os.close(self.w)
        try:
            return self.p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()
            return None

INIT = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"processId": None, "rootUri": None, "capabilities": {}}},
        {"jsonrpc": "2.0", "method": "initialized", "params": {}}]

def stepwise(steps, env, cwd=None):
    """Each step after the previous step's publish (an editor's pace)."""
    lv = Live(INIT + [steps[0]], env, cwd)
    lv.publish()
    for s in steps[1:]:
        lv.send(s)
        lv.publish()  # didClose publishes the empty list
    rc = lv.finish()
    return rc, lv.out

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
# The stderr log names what it handled, as text (#4565: these were
# eprints_cstr chains; the uri now comes as a StrView from the JSON value).
log_msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"processId": None, "rootUri": None, "capabilities": {}}},
            did_open(uri, "fn f() -> i32\n    0\n"),
            did_change(uri, "fn g() -> i32\n    0\n", 2),
            {"jsonrpc": "2.0", "method": "textDocument/didClose",
             "params": {"textDocument": {"uri": uri}}},
            {"jsonrpc": "2.0", "id": 7, "method": "no/such-method"},
            {"jsonrpc": "2.0", "id": 99, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"}]
p = subprocess.run([BIN], input=b"".join(map(frame, log_msgs)),
                   capture_output=True, timeout=20, env=NO_RITZ1)
log = p.stderr.decode(errors="replace")
for line in (f"[ritz-lsp] Document opened: {uri}\n",
             f"[ritz-lsp] Document changed: {uri}\n",
             f"[ritz-lsp] Document closed: {uri}\n",
             "[ritz-lsp] Unknown method: no/such-method\n",
             "[ritz-lsp] Handling shutdown\n"):
    check("stderr log has " + repr(line), line in log, repr(log[-400:]))

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

# --- hover / definition across imports (#3884) ------------------------------
# A fn the document imports is found in the imported file, resolved the way
# ritz1 resolves it with the -I diagnostics passes: the document's directory
# and its ancestors, the monorepo's projects/ritz (ritzlib), then $RITZ_PATH
# (<entry>/<pkg>/<rest>.ritz, then <pkg>/lib/ and <pkg>/src/). A module's own
# imports resolve from that module's directory. What a module exports is its
# `pub` fns and, through `pub import`, what those modules export; a plain
# import of an imported module is private to it (#3891), and so is a fn
# without `pub`. The tree's path has a space, so the Location's uri must be
# percent-encoded the way an editor encodes it.
RITZLIB_STR = REAL_RITZ1.parents[2] / "ritzlib" / "cstr.ritz"
tree = scratch / "imp tree"
files = {
    "app/util.ritz": "pub import reexp\nimport plain\n\npub fn util_fn() -> i32\n    1\n\nfn private_fn() -> i32\n    2\n",
    "app/reexp.ritz": "pub import util\n\n# a cycle back to util\npub fn reexported(a: i32,  b: i32) -> i32\n    a\n",
    "app/plain.ritz": "pub fn transitive_plain() -> i32\n    3\n",
    "lib/deep.ritz": "pub import deepsib\n\n    pub fn deep_fn(x: i32) -> i32   \npub import ritzlib.memory\n",
    # ritz1 resolves a ritzlib import only from its roots, never from the
    # importing module's directory, so this file is never read.
    "lib/ritzlib/memory.ritz": "pub fn decoy_mem() -> i32\n    7\n",
    "lib/deepsib.ritz": "pub fn deepsib_fn() -> i32\n    4\n",
    "deepsib.ritz": "pub fn decoy() -> i32\n    5\n",
    "ext/extpkg/lib/thing.ritz": "pub fn ext_fn() -> i32\n    6\n",
    "ext/extpkg/src/other.ritz": "pub fn ext_src_fn() -> i32\n    8\n",
}
for rel, text in files.items():
    (tree / rel).parent.mkdir(parents=True, exist_ok=True)
    (tree / rel).write_text(text)
# tree/deepsib.ritz is an ancestor of lib/ too, but lib/'s own directory is
# probed first, so lib/deepsib.ritz answers.
iuri = (tree / "app" / "main.ritz").as_uri()
isrc = ("import ritzlib.cstr\n"                                      # 0
        "import util\n"                                             # 1
        "import lib.deep { deep_fn }\n"                             # 2
        "import extpkg.thing\n"                                     # 3
        "import extpkg.other\n"                                     # 4
        "fn main() -> i32\n"                                        # 5
        "    strlen(c\"x\") + util_fn() + deep_fn(1) + reexported(1, 2)\n"   # 6
        "    deepsib_fn() + ext_fn() + transitive_plain() + private_fn() + nowhere()\n"  # 7
        "    ext_src_fn() + decoy_mem()  # import plain\n")              # 8
L6 = isrc.splitlines()[6]
L7 = isrc.splitlines()[7]
L8 = isrc.splitlines()[8]
def at(line_text, name):
    return line_text.index(name + "(")
strlen_line = next(i for i, l in enumerate(RITZLIB_STR.read_text().splitlines())
                   if l.startswith("pub fn strlen("))
ireqs = [
    req(2, "textDocument/definition", iuri, 6, at(L6, "strlen")),
    req(3, "textDocument/hover", iuri, 6, at(L6, "strlen")),
    req(4, "textDocument/definition", iuri, 6, at(L6, "util_fn") + 2),
    req(5, "textDocument/definition", iuri, 6, at(L6, "deep_fn")),
    req(6, "textDocument/hover", iuri, 6, at(L6, "deep_fn")),
    req(7, "textDocument/definition", iuri, 6, at(L6, "reexported")),
    req(8, "textDocument/hover", iuri, 6, at(L6, "reexported")),
    req(9, "textDocument/definition", iuri, 7, at(L7, "deepsib_fn")),
    req(10, "textDocument/definition", iuri, 7, at(L7, "ext_fn")),
    req(11, "textDocument/definition", iuri, 7, at(L7, "transitive_plain")),
    req(12, "textDocument/hover", iuri, 7, at(L7, "transitive_plain")),
    req(13, "textDocument/definition", iuri, 7, at(L7, "private_fn")),
    req(14, "textDocument/definition", iuri, 7, at(L7, "nowhere")),
    req(15, "textDocument/definition", "untitled:Untitled-1", 1, 4),
    req(16, "textDocument/definition", iuri, 8, 4),
    req(17, "textDocument/definition", iuri, 8, at(L8, "decoy_mem")),
]
IENV = {**NO_RITZ1, "RITZ_PATH": str(tree / "ext")}
rc, out = session([did_open(iuri, isrc), did_open("untitled:Untitled-1", "import ritzlib.cstr\n    strlen(c\"\")\n"),
                   *ireqs], env=IENV)
r = by_id(out)
def res(rid):
    return r.get(rid, {}).get("result")
def loc(rel, line, ch, name):
    return {"uri": (tree / rel).as_uri(), "range": rng(line, ch, line, ch + len(name))}
str_loc = {"uri": RITZLIB_STR.as_uri(), "range": rng(strlen_line, 7, strlen_line, 13)}
check("import: definition of a ritzlib fn -> its declaration in ritzlib",
      res(2) == str_loc, repr(r.get(2)))
check("import: hover on a ritzlib fn -> its signature from ritzlib, range in the document",
      (res(3) or {}).get("contents", {}).get("value") == "```ritz\npub fn strlen(s: *u8) -> i64\n```"
      and (res(3) or {}).get("range") == rng(6, at(L6, "strlen"), 6, at(L6, "strlen") + 6), repr(r.get(3)))
check("import: definition of a sibling module's fn (uri percent-encoded)",
      res(4) == loc("app/util.ritz", 3, 7, "util_fn"), repr(r.get(4)))
check("import: definition through a dotted import found in an ancestor directory",
      res(5) == loc("lib/deep.ritz", 2, 11, "deep_fn"), repr(r.get(5)))
check("import: hover on an imported fn -> its line, trimmed",
      (res(6) or {}).get("contents", {}).get("value") == "```ritz\npub fn deep_fn(x: i32) -> i32\n```",
      repr(r.get(6)))
check("import: a `pub import`ed module's fn is visible (and a cycle ends)",
      res(7) == loc("app/reexp.ritz", 3, 7, "reexported"), repr(r.get(7)))
check("import: hover through a `pub import`",
      (res(8) or {}).get("contents", {}).get("value") == "```ritz\npub fn reexported(a: i32,  b: i32) -> i32\n```",
      repr(r.get(8)))
check("import: a module's own imports resolve from its directory",
      res(9) == loc("lib/deepsib.ritz", 0, 7, "deepsib_fn"), repr(r.get(9)))
check("import: $RITZ_PATH resolves, with the <pkg>/lib/ probe",
      res(10) == loc("ext/extpkg/lib/thing.ritz", 0, 7, "ext_fn"), repr(r.get(10)))
for rid, what in ((11, "definition of a fn only reachable through a plain import of an import"),
                  (12, "hover on a fn only reachable through a plain import of an import"),
                  (13, "definition of an imported module's private fn"),
                  (14, "definition of a fn no import declares"),
                  (17, "definition of a fn in a ritzlib/ beside an importing module, not in ritzlib")):
    check("import: " + what + " -> null",
          rid in r and "error" not in r[rid] and r[rid].get("result") is None, repr(r.get(rid)))
check("import: $RITZ_PATH's <pkg>/src/ probe",
      res(16) == loc("ext/extpkg/src/other.ritz", 0, 7, "ext_src_fn"), repr(r.get(16)))
check("import: a non-file document still resolves ritzlib",
      res(15) == str_loc, repr(r.get(15)))
check("import: clean exit", rc == 0, f"exit {rc}")

# --- positions are UTF-16 code units (#3885) --------------------------------
# LSP's `character` counts UTF-16 code units; the server works in bytes. A line
# with é (2 bytes, 1 unit), € (3 bytes, 1 unit) and 😀 (4 bytes, a surrogate
# pair: 2 units) before a name puts it 9 bytes but 4 units further along.
# The server must not claim another encoding, even when the client offers one.
def u16(s):
    return len(s.encode("utf-16-le")) // 2
MB = "é€😀"
uuri = "file:///tmp/t3885.ritz"
usrc = ("fn helper() -> i32\n"                                   # 0
        "    0\n"                                                # 1
        "fn main() -> i32\n"                                     # 2
        f"    later(c\"{MB}\") + helper() + later(c\"{MB}{MB}\")\n"  # 3
        "fn later(s: *u8) -> i32\n"                              # 4
        "    1\n")                                               # 5
UL3 = usrc.splitlines()[3]
hc = u16(UL3[:UL3.index("helper")])   # helper's first unit
sc = u16(UL3[:UL3.rindex("later")])   # the second later, after 3 runs
check("utf-16: test line really differs in bytes and units",
      len(UL3[:UL3.index("helper")].encode()) - hc == 5, repr(hc))
ureqs = [
    req(2, "textDocument/hover", uuri, 3, hc),
    req(3, "textDocument/definition", uuri, 3, hc + 2),   # inside helper
    req(4, "textDocument/hover", uuri, 3, hc + 6),        # `(` just past it
    req(5, "textDocument/hover", uuri, 3, sc + 2),
    req(6, "textDocument/definition", uuri, 3, u16(UL3) + 3),  # past the line
]
init_utf8 = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"processId": None, "rootUri": None,
                        "capabilities": {"general": {"positionEncodings": ["utf-8", "utf-16"]}}}}
p = subprocess.run([BIN], input=b"".join(map(frame, [
        init_utf8, {"jsonrpc": "2.0", "method": "initialized", "params": {}},
        did_open(uuri, usrc), *ureqs,
        {"jsonrpc": "2.0", "id": 99, "method": "shutdown"},
        {"jsonrpc": "2.0", "method": "exit"}])), capture_output=True, timeout=20, env=NO_RITZ1)
out = [json.loads(p.stdout[m.end():m.end() + int(m.group(1))])
       for m in re.finditer(rb"Content-Length: (\d+)\r\n\r\n", p.stdout)]
r = by_id(out)
caps = r.get(1, {}).get("result", {}).get("capabilities") or {}
check("utf-16: a client offering utf-8 still gets utf-16 positions",
      caps.get("positionEncoding", "utf-16") == "utf-16", repr(caps))
h = r.get(2, {}).get("result") or {}
check("utf-16: hover after é€😀 finds the name at that unit",
      h.get("contents", {}).get("value") == "```ritz\nfn helper() -> i32\n```", repr(r.get(2)))
check("utf-16: hover range after é€😀 is in units",
      h.get("range") == rng(3, hc, 3, hc + 6), repr(h))
check("utf-16: definition from inside the name",
      r.get(3, {}).get("result") == {"uri": uuri, "range": rng(0, 3, 0, 9)}, repr(r.get(3)))
check("utf-16: hover just past the name -> null",
      4 in r and "error" not in r[4] and r[4].get("result") is None, repr(r.get(4)))
h = r.get(5, {}).get("result") or {}
check("utf-16: hover after two runs of é€😀, range in units",
      h.get("contents", {}).get("value") == "```ritz\nfn later(s: *u8) -> i32\n```"
      and h.get("range") == rng(3, sc, 3, sc + 5), repr(r.get(5)))
check("utf-16: a position past the end of the line -> null",
      6 in r and "error" not in r[6] and r[6].get("result") is None, repr(r.get(6)))

# --- the same document sent with \uXXXX escapes (#3914) ---------------------
# é€😀 escaped as \u00e9 \u20ac \ud83d\ude00 must decode to the same buffer as
# the raw-UTF-8 run above: the pair combined into one 4-byte sequence, so the
# positions after it land where they did.  Undecoded, each escape stays six
# ASCII bytes ("u00e9"...) and every unit after it shifts.
check("escaped: the frame carries \\u00e9, \\u20ac and a surrogate pair",
      all(e in frame_escaped(did_open(uuri, usrc))
          for e in (b"\\u00e9", b"\\u20ac", b"\\ud83d\\ude00")), "")
rc, out = session([did_open(uuri, usrc), *ureqs[:4]], env=NO_RITZ1, framer=frame_escaped)
r = by_id(out)
h = r.get(2, {}).get("result") or {}
check("escaped: hover after \\u-escaped é€😀 finds the name, range in units",
      h.get("contents", {}).get("value") == "```ritz\nfn helper() -> i32\n```"
      and h.get("range") == rng(3, hc, 3, hc + 6), repr(r.get(2)))
check("escaped: definition from inside the name",
      r.get(3, {}).get("result") == {"uri": uuri, "range": rng(0, 3, 0, 9)}, repr(r.get(3)))
check("escaped: hover just past the name -> null",
      4 in r and "error" not in r[4] and r[4].get("result") is None, repr(r.get(4)))
h = r.get(5, {}).get("result") or {}
check("escaped: hover after two escaped runs, range in units",
      h.get("contents", {}).get("value") == "```ritz\nfn later(s: *u8) -> i32\n```"
      and h.get("range") == rng(3, sc, 3, sc + 5), repr(r.get(5)))
check("escaped: clean exit", rc == 0, f"exit {rc}")

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
rc, out = stepwise([did_open(duri, bad, 1), did_change(duri, "fn main() -> i32\n    0\n", 2),
                    did_change(duri, mixed, 3), did_change(duri, silent_fail, 4),
                    {"jsonrpc": "2.0", "method": "textDocument/didClose",
                     "params": {"textDocument": {"uri": duri}}}], env=STUB)
d = diags(out)
check("stub: didClose clears the document's diagnostics",
      d[-1:] == [{"uri": duri, "diagnostics": []}], repr(d[-1:]))
d = d[:-1]
check("stub: one publishDiagnostics per open/change sent after the last publish",
      len(d) == 4, repr(d))
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
check("stub: ritz1 ran once per open/change sent after the last publish", len(calls) == 4, repr(calls))
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

# Where the scratch copy goes without $XDG_RUNTIME_DIR: ritzlib.fs temp_dir
# (AGAST #4957), so $TMPDIR when it is a directory by an absolute path, else
# /tmp; an unusable $TMPDIR no longer loses the compile.
def scratch_input(tmpdir):
    env = {k: v for k, v in STUB.items() if k != "XDG_RUNTIME_DIR"}
    env["TMPDIR"] = tmpdir
    before = len(log.read_text().splitlines()) if log.exists() else 0
    rc, out = stepwise([did_open(duri, "fn main() -> i32\n    0\n", 1)], env=env)
    lines = log.read_text().splitlines()[before:] if log.exists() else []
    d = diags(out)
    return (json.loads(lines[-1])["argv"][0] if lines else ""), d
tmpd = scratch / "tmpd"
tmpd.mkdir()
uid_dir = f"ritz-lsp-{os.getuid()}"
got, _ = scratch_input(str(tmpd))
check("scratch: under $TMPDIR when it is a directory",
      got.startswith(str(tmpd / uid_dir) + "/"), repr(got))
# An unusable $TMPDIR (relative) still compiles, in temp_dir's fallback: an
# absolute <temp>/ritz-lsp-<uid>/. Which directory that is (/tmp) is pinned
# by ritzlib's test_temp_dir_from_falls_back_to_tmp; naming the host's here
# would share it (AGAST #3178).
got, d = scratch_input("relative/not-a-dir")
check("scratch: an unusable $TMPDIR falls back to temp_dir's default",
      os.path.isabs(got) and f"/{uid_dir}/" in got and not got.startswith("relative")
      and d[-1:] and d[-1].get("diagnostics") == [], repr((got, d)))

# ritz1 reports byte columns; the diagnostic's are UTF-16 units (#3885).
# Line 2 below has é€😀 before `nope` (9 bytes, 4 units); the stub reports
# the byte column, computed here rather than hand-counted.
mb_line = f"    f(c\"{MB}\", nope(1))"
mb_byte_col = len(mb_line[:mb_line.index("nope")].encode()) + 1
mb_u16 = u16(mb_line[:mb_line.index("nope")])
mb_doc = (f"#! {{in}}:2:{mb_byte_col}: error: Unknown function: nope\n" + mb_line + "\n"
          f"#! {{in}}:2:{len(mb_line.encode()) + 3}: error: past the line end\n#exit 1\n")
rc, out = session([did_open(duri, mb_doc, 1)], env=STUB)
got = ((diags(out) or [{}])[0].get("diagnostics") or []) + [{}, {}]
check("stub: a byte column after é€😀 becomes a UTF-16 range over the name",
      got[0].get("range") == rng(1, mb_u16, 1, mb_u16 + 4), repr(got[0]))
check("stub: a byte column past the line end stays past it, in units",
      got[1].get("range", {}).get("start") == {"line": 1, "character": u16(mb_line) + 2}, repr(got[1]))

# ritz1's line and column are read by ritzlib's strview_parse_i64 (#4040):
# one that is not an i64 >= 1 leaves the line unlocated (line 0, the whole
# line as the message). The hand-written loop wrapped 2^64 + 1 round to 1
# and put the error on the document's first line.
num_cases = [  # (line:col, located start or None)
    ("9223372036854775807:1", {"line": 9223372036854775806, "character": 0}),
    ("0:1", None),
    ("9223372036854775808:1", None),
    ("18446744073709551617:1", None),
    ("1:18446744073709551617", None),
    ("-9223372036854775808:1", None),
    ("1x:1", None)]
num_doc = "".join(f"#! {{in}}:{pos}: error: case {k}\n"
                  for k, (pos, _) in enumerate(num_cases)) + "#exit 1\n"
rc, out = session([did_open(duri, num_doc, 1)], env=STUB)
got = ((diags(out) or [{}])[0].get("diagnostics") or []) + [{}] * len(num_cases)
for k, (pos, start) in enumerate(num_cases):
    g = got[k]
    if start is None:
        ok = (g.get("range") == rng(0, 0, 0, 0)
              and g.get("message", "").endswith(f":{pos}: error: case {k}"))
    else:
        ok = g.get("range", {}).get("start") == start and g.get("message") == f"case {k}"
    check(f"stub: line:col {pos} -> {'located' if start else 'unlocated'}", ok, repr(g))

# --- a burst of changes compiles once, for the last version (#3902) ---------
# Everything up to the first publish is in the server's stdin before it reads
# any of it: two documents opened, one changed three times, then a hover. The
# server answers the hover, compiles each document once for its latest text,
# and publishes that version only. A change sent after that publish still
# gets its own. The stub records each compile's text.
log.unlink(missing_ok=True)
buri = (docdir / "burst.ritz").as_uri()
ouri = (docdir / "other.ritz").as_uri()
vtext = lambda v: f"# version {v}\n#! {{in}}:1:1: error: v{v}\n#exit 1\n"
lv = Live(INIT + [did_open(buri, vtext(1), 1), did_open(ouri, vtext(10), 10),
                  did_change(buri, vtext(2), 2), did_change(buri, vtext(3), 3),
                  did_change(buri, vtext(4), 4), req(2, "textDocument/hover", buri, 0, 0)], STUB)
lv.until(lambda m: m.get("id") == 2)
if len(diags(lv.out)) < 2:
    lv.until(lambda m: len(diags(lv.out)) >= 2)
lv.send(req(3, "textDocument/hover", buri, 0, 0))   # a round trip: nothing else queued
lv.until(lambda m: m.get("id") == 3)
burst = diags(lv.out)
check("burst: one publish per document, for its last version",
      sorted((x["uri"], x["version"]) for x in burst) == sorted([(buri, 4), (ouri, 10)]),
      repr([(x["uri"], x["version"]) for x in burst]))
check("burst: the published diagnostics are the last version's",
      [x["diagnostics"][0]["message"] for x in burst if x["uri"] == buri] == ["v4"], repr(burst))
calls = [json.loads(l)["text"] for l in log.read_text().splitlines()] if log.exists() else []
check("burst: ritz1 ran once per document, on the last text",
      sorted(calls) == sorted([vtext(4), vtext(10)]), repr(calls))
kinds = [m.get("id", m.get("method")) for m in lv.out]
check("burst: a request in the burst is answered before the compiles",
      2 in kinds and "textDocument/publishDiagnostics" in kinds
      and kinds.index(2) < kinds.index("textDocument/publishDiagnostics"), repr(kinds))
lv.send(did_change(buri, vtext(5), 5))
p5 = (lv.publish() or {}).get("params")
check("burst: a change after the publish gets its own",
      p5 is not None and p5.get("version") == 5
      and (p5.get("diagnostics") or [{}])[0].get("message") == "v5", repr(p5))
check("burst: clean exit", lv.finish() == 0, "")
check("burst: nothing else published", len(diags(lv.out)) == 3, repr(diags(lv.out)))

# Every open document is published even if input never pauses: shutdown
# right behind the burst still gets each one's last version, before its reply.
rc, out = session([did_open(buri, vtext(1), 1), did_change(buri, vtext(2), 2)], env=STUB)
kinds = [m.get("id", m.get("method")) for m in out]
check("burst: shutdown publishes what is still pending, before replying",
      [(x["uri"], x["version"]) for x in diags(out)] == [(buri, 2)]
      and kinds[-2:] == ["textDocument/publishDiagnostics", 99], repr(kinds))

# --- a ritz1 that hangs (#3883) ---------------------------------------------
# The stub records its pid and sleeps, holding stderr open. The server must
# kill it at its deadline (COMPILE_DEADLINE_SECS, 5s), publish one warning,
# reap it (checked while the server still runs: an unreaped child stays in
# /proc as a zombie) and go on answering. Everything here is bounded, so a
# regression fails in ~12s instead of hanging the suite.
import select, signal, time
DEADLINE = 5
hang_pid = scratch / "hang.pid"
hang = scratch / "ritz1-hang"
hang.write_text(f"""#!{sys.executable} -I
import os, time
open({str(hang_pid)!r}, "w").write(str(os.getpid()))
time.sleep(3600)
""")
hang.chmod(0o755)
srv = subprocess.Popen([BIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, env={**os.environ, "RITZ1": str(hang)})
got, buf, hover = [], b"", None
t0 = time.monotonic()
diag_at = None
try:
    srv.stdin.write(b"".join(map(frame, [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"processId": None, "rootUri": None, "capabilities": {}}},
        {"jsonrpc": "2.0", "method": "initialized", "params": {}},
        did_open(duri, "fn helper() -> i32\n    1\n")])))
    srv.stdin.flush()
    end = t0 + DEADLINE + 7
    while hover is None and time.monotonic() < end:
        if not select.select([srv.stdout], [], [], end - time.monotonic())[0]:
            break
        chunk = os.read(srv.stdout.fileno(), 65536)
        if not chunk:
            break
        buf += chunk
        while (m := re.search(rb"Content-Length: (\d+)\r\n\r\n", buf)) and len(buf) >= m.end() + int(m.group(1)):
            msg = json.loads(buf[m.end():m.end() + int(m.group(1))])
            buf = buf[m.end() + int(m.group(1)):]
            got.append(msg)
            if msg.get("method") == "textDocument/publishDiagnostics" and diag_at is None:
                diag_at = time.monotonic() - t0
                # The request comes after the timed-out compile, not with
                # the open: a request queued behind a change is answered
                # before the compile (#3902).
                srv.stdin.write(frame(req(2, "textDocument/hover", duri, 0, 4)))
                srv.stdin.flush()
            if msg.get("id") == 2:
                hover = msg
    pid = int(hang_pid.read_text()) if hang_pid.exists() else None
    alive = pid is not None and os.path.exists(f"/proc/{pid}")
    state = ""
    if alive:
        try:
            state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        except OSError:
            alive = False
    d = diags(got)
    check("hang: one warning that the check timed out",
          len(d) == 1 and len(d[0]["diagnostics"]) == 1 and d[0]["diagnostics"][0]["severity"] == 2
          and "timed out" in d[0]["diagnostics"][0]["message"], repr(d))
    check("hang: published at the deadline, not long after",
          diag_at is not None and DEADLINE - 1 <= diag_at <= DEADLINE + 3, repr(diag_at))
    check("hang: a later request is still answered",
          hover is not None and (hover.get("result") or {}).get("contents") is not None, repr(hover))
    check("hang: ritz1 ran", pid is not None, "no pid file")
    check("hang: ritz1 killed and reaped (no process, no zombie)", not alive,
          f"pid {pid} still in /proc, state {state!r}")
    if hover is not None:
        srv.stdin.write(frame({"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
                        + frame({"jsonrpc": "2.0", "method": "exit"}))
        srv.stdin.close()
        try:
            check("hang: clean exit", srv.wait(timeout=5) == 0, f"exit {srv.returncode}")
        except subprocess.TimeoutExpired:
            check("hang: clean exit", False, "server did not exit")
finally:
    if srv.poll() is None:
        srv.kill()
        srv.wait()
    if hang_pid.exists():
        try:
            os.kill(int(hang_pid.read_text()), signal.SIGKILL)
        except (OSError, ValueError):
            pass

# --- diagnostics from the real ritz1 ----------------------------------------
if REAL_RITZ1.is_file():
    env = {k: v for k, v in os.environ.items() if k not in ("RITZ1", "RITZ_PATH")}
    ruri = (docdir / "real.ritz").as_uri()
    undefined = "fn main() -> i32\n    nope(1)\n"
    uses_ritzlib = 'import ritzlib.fmt\n\nfn main() -> i32\n    print("hi\\n")\n    0\n'
    rc, out = stepwise([did_open(ruri, undefined, 1), did_change(ruri, uses_ritzlib, 2)],
                       env=env, cwd=str(scratch))
    d = diags(out) + [{}, {}]
    got = d[0].get("diagnostics") or [{}]
    check("ritz1: a call to an undefined fn is an error at the call",
          len(got) == 1 and got[0].get("range") == rng(1, 4, 1, 8) and got[0].get("severity") == 1
          and "nope" in got[0].get("message", ""), repr(d[0]))
    check("ritz1: ritzlib imports resolve with no RITZ_PATH set",
          d[1].get("diagnostics") == [], repr(d[1]))
    # ritz1's byte column becomes UTF-16 units after é€😀 (#3885).
    mb_src = f'import ritzlib.cstr\n\nfn main() -> i32\n    (strlen(c"{MB}") + nope(1)) as i32\n'
    mb_l3 = mb_src.splitlines()[3]
    mc = u16(mb_l3[:mb_l3.index("nope")])
    rc, out = session([did_open(ruri, mb_src, 1)], env=env, cwd=str(scratch))
    got = (diags(out) or [{}])[0].get("diagnostics") or [{}]
    check("ritz1: an error after é€😀 is at its UTF-16 column",
          len(got) == 1 and got[0].get("range") == rng(3, mc, 3, mc + 4)
          and "nope" in got[0].get("message", ""), repr(got))
else:
    print(f"skip: real ritz1 not built ({REAL_RITZ1}); make -C projects/ritz ritz1")

shutil.rmtree(scratch, ignore_errors=True)
if fails:
    print(f"{len(fails)} ritz-lsp check(s) failed")
    sys.exit(1)
PY
