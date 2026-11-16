"""rzsh (#2461): the Linux shell, a scripted session per feature: echo, cd,
$X, $?, >, |, external commands, EOF."""

from __future__ import annotations

import subprocess
from functools import partial
from pathlib import Path

from .harness import CheckFailed, Reporter, binary, run_cmd, short


def session(work: Path, script: str) -> tuple[subprocess.CompletedProcess, list[str]]:
    rzsh = binary("rzsh/build/debug/rzsh.linux")
    res = run_cmd([str(rzsh)], work, stdin=(script + "\nexit\n").encode(), timeout=5)
    return res, [ln.strip() for ln in res.stdout.decode(errors="replace").splitlines()]


def expect_line(work: Path, script: str, want: str) -> None:
    res, lines = session(work, script)
    # Exact lines only: rzsh echoes each input after its prompt
    # ("rzsh> echo X=$X"), so a suffix match would pass on the echo.
    if want not in lines:
        raise CheckFailed(f"{script!r} -> {short(res.stdout, 120)}")


def redirect(work: Path) -> None:
    out = work / "out.txt"
    out.unlink(missing_ok=True)
    res, _ = session(work, f"echo redirected > {out}")
    if not out.exists() or out.read_text().strip() != "redirected":
        raise CheckFailed(f"'echo redirected > out.txt' -> file {'missing' if not out.exists() else repr(out.read_text())}; "
                          f"stdout {short(res.stdout, 80)}")


def eof(work: Path) -> None:
    # No trailing `exit`: end of stdin must end the shell (it used to spin).
    rzsh = binary("rzsh/build/debug/rzsh.linux")
    res = run_cmd([str(rzsh)], work, stdin=b"echo before-eof\n", timeout=5)
    if res.returncode != 0 or "before-eof" not in res.stdout.decode(errors="replace").split():
        raise CheckFailed(f"rc={res.returncode} stdout {short(res.stdout, 80)}")


def suite_rzsh(r: Reporter, tmp: Path) -> None:
    work = tmp / "rzsh"
    (work / "sub").mkdir(parents=True)
    lines = (("echo", "echo hello world", "hello world"),
             ("external", "/bin/echo external-ok", "external-ok"),
             ("cd", f"cd {work / 'sub'}\npwd", str(work / "sub")),
             ("var", "export X=5\necho X=$X", "X=5"),
             ("status", "false\necho status=$?", "status=1"))
    for name, script, want in lines:
        r.run(f"rzsh.{name}", partial(expect_line, work, script, want))
    r.run("rzsh.redirect", partial(redirect, work))
    r.run("rzsh.pipe", partial(expect_line, work, "echo piped | /usr/bin/tr p P", "PiPed"))
    r.run("rzsh.eof", partial(eof, work))
