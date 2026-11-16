"""hollow entry points (#2460): sage, goliath, rzrz and ritz-lsp must not
report success for work they did not do."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

from .harness import REPO, Broken, CheckFailed, Reporter, binary, run_cmd, short

LSP_SRC = "fn helper() -> i32\n    42\n\nfn main() -> i32\n    helper()\n"


def lsp_frame(obj: dict) -> bytes:
    b = json.dumps(obj).encode()
    return b"Content-Length: %d\r\n\r\n%s" % (len(b), b)


def lsp_session(lsp: Path, cwd: Path, src: str, uri: str, requests: list[tuple[str, dict]]) -> list[dict]:
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"processId": None, "rootUri": cwd.as_uri(), "capabilities": {}}},
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
            {"jsonrpc": "2.0", "method": "textDocument/didOpen",
             "params": {"textDocument": {"uri": uri, "languageId": "ritz", "version": 1, "text": src}}}]
    for i, (method, params) in enumerate(requests, start=2):
        msgs.append({"jsonrpc": "2.0", "id": i, "method": method, "params": params})
    msgs += [{"jsonrpc": "2.0", "id": 99, "method": "shutdown"}, {"jsonrpc": "2.0", "method": "exit"}]
    res = run_cmd([str(lsp)], cwd, stdin=b"".join(lsp_frame(m) for m in msgs), timeout=6)
    out, replies = res.stdout, []
    for m in re.finditer(rb"Content-Length: (\d+)\r\n\r\n", out):
        n = int(m.group(1))
        try:
            replies.append(json.loads(out[m.end():m.end() + n]))
        except ValueError:
            pass
    return replies


def sage_runs_js(work: Path) -> None:
    sage = binary("sage/build/debug/sage")
    (work / "t.js").write_text("console.log(6 * 7);\n")
    res = run_cmd([str(sage), "t.js"], work)
    if res.returncode != 0 or not re.search(rb"(?m)^42$", res.stdout):
        raise CheckFailed(f"sage t.js (console.log(6*7)) -> exit {res.returncode}: {short(res.stdout, 80)}")


def sage_no_false_success(work: Path) -> None:
    # Whatever sage can do, exit 0 on a script means it ran it (#2460).
    sage = binary("sage/build/debug/sage")
    (work / "t.js").write_text("console.log(6 * 7);\n")
    res = run_cmd([str(sage), "t.js"], work)
    if res.returncode == 0 and not re.search(rb"(?m)^42$", res.stdout):
        raise CheckFailed(f"sage t.js -> exit 0 without running it: {short(res.stdout, 80)}")


def goliath_unknown(work: Path) -> None:
    goliath = binary("goliath/build/debug/goliath")
    res = run_cmd([str(goliath), "no-such-command-2456"], work)
    if res.returncode == 0:
        raise CheckFailed(f"unknown command, exit 0: {short(res.stdout, 80)}")


def rzrz_sub(sub: str) -> None:
    # rzrz: a subcommand on a project that does not exist did no work, so it
    # must not exit 0, whether it is implemented or honestly "not implemented".
    rzrz = binary("rzrz/build/debug/rzrz")
    res = run_cmd([str(rzrz), sub, "no-such-project-2456"], REPO)
    if res.returncode == 0:
        raise CheckFailed(f"rzrz {sub} no-such-project -> exit 0: {short(res.stdout, 80)}")


@dataclass
class LspCtx:
    """One ritz-lsp session, run on first use, its replies shared by the checks."""
    work: Path
    cache: dict[int, dict] = field(default_factory=dict)

    @property
    def path(self) -> Path:
        return self.work / "t.ritz"


def lsp_replies(ctx: LspCtx) -> dict[int, dict]:
    if not ctx.cache:
        lsp = binary("ritz-lsp/build/debug/ritz-lsp")
        pos = {"textDocument": {"uri": ctx.path.as_uri()}, "position": {"line": 4, "character": 6}}
        replies = lsp_session(lsp, ctx.work, LSP_SRC, ctx.path.as_uri(),
                              [("textDocument/hover", pos), ("textDocument/definition", pos)])
        ctx.cache.update({m["id"]: m for m in replies if "id" in m})
        if 1 not in ctx.cache:
            raise Broken(f"ritz-lsp never answered initialize ({len(replies)} replies)")
    return ctx.cache


def lsp_cap(ctx: LspCtx, cap: str, rid: int, what: str) -> str | None:
    """ritz-lsp: a capability it advertises must answer for a symbol it can see."""
    replies = lsp_replies(ctx)
    caps = replies[1].get("result", {}).get("capabilities", {})
    if not caps.get(cap):
        return f"{cap} not advertised"
    if rid not in replies:
        raise Broken(f"ritz-lsp sent no reply to {what} (the xfail is about a null answer)")
    if not replies[rid].get("result"):
        raise CheckFailed(f"advertises {cap}, {what} on helper() -> {json.dumps(replies[rid].get('result'))}")
    return None


def suite_hollow(r: Reporter, tmp: Path) -> None:
    work = tmp / "hollow"
    work.mkdir()
    r.run("hollow.sage_runs_js", partial(sage_runs_js, work))
    r.run("hollow.sage_no_false_success", partial(sage_no_false_success, work))
    r.run("hollow.goliath_unknown_command", partial(goliath_unknown, work))
    for sub in ("test", "run", "clean", "compare"):
        r.run(f"hollow.rzrz_{sub}", partial(rzrz_sub, sub))
    ctx = LspCtx(work)
    ctx.path.write_text(LSP_SRC)
    r.run("hollow.lsp_hover", partial(lsp_cap, ctx, "hoverProvider", 2, "hover"))
    r.run("hollow.lsp_definition", partial(lsp_cap, ctx, "definitionProvider", 3, "definition"))
