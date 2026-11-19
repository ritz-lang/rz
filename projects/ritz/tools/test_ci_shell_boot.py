#!/usr/bin/env python3
"""CI must boot harland to an rzsh prompt and drive it over serial (AGAST #4252).

projects/harland/tools/test_shell_boot.sh boots the `make -C projects/indium
shell` image (init_interactive as /bin/init) under OVMF, and
tools/shell_session.py types a scripted session on COM1: echo, pwd, ls /bin,
cat /etc/motd, a command after cat exits, then `exit`, which returns to
init_interactive ("[init] Shell exited", #1882); init then exits and the VM
powers off.

These tests pin, as test_ci_nvme_boot.py does for its boot:

  * the wiring: the step runs after the NVMe boots and before the log
    upload, gates for real and has a timeout; `make shell` boots the same
    image on -serial mon:stdio;
  * the verdicts: a missing tool is a SETUP ERROR (exit 3), a missing prompt
    or a wrong answer is exit 1. The script runs against a stub QEMU that
    plays a guest on the serial socket, so no QEMU, OVMF or kernel build is
    needed.

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_shell_boot.py -q
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ci_local  # noqa: E402

REPO = ci_local.REPO_ROOT
SHELL_SCRIPT = "projects/harland/tools/test_shell_boot.sh"
NVME_SCRIPT = "projects/harland/tools/test_nvme_boot.sh"

# A guest on the serial socket: connects to the -chardev socket path, prints
# $FAKE_BANNER, then answers each typed line from the JSON map $FAKE_REPLIES
# (missing: no output) followed by $FAKE_PROMPT. `exit` sends $FAKE_EXIT and
# exits with $FAKE_EXIT_RC (0 = a guest power-off). Every argv goes to
# $STUB_LOG.
#
# It is a terminal too (#4254): DEL rubs out a byte (BS SP BS), `cat` is
# blocked in a cooked read (each line it reads is echoed back) and `spin`
# never prompts; Ctrl-C prints ^C and ends either one at a fresh prompt (or
# drops the line at the prompt). $FAKE_NO_RUBOUT=1 takes DEL as a byte and
# $FAKE_NO_INTR=1 ignores Ctrl-C.
QEMU_STUB = r"""#!/usr/bin/env python3
import json, os, socket, sys, time
open(os.environ["STUB_LOG"], "a").write(" ".join(sys.argv[1:]) + "\n")
args = sys.argv[1:]
path = [a for a in args if a.startswith("socket,id=con,")][0].split("path=")[1].split(",")[0]
s = socket.socket(socket.AF_UNIX)
s.connect(path)
prompt = os.environ.get("FAKE_PROMPT", "rzsh> ").encode()
replies = json.loads(os.environ.get("FAKE_REPLIES", "{}"))
rubout = os.environ.get("FAKE_NO_RUBOUT") != "1"
intr = os.environ.get("FAKE_NO_INTR") != "1"
s.sendall(os.environ.get("FAKE_BANNER", "").encode())
if os.environ.get("FAKE_NO_PROMPT") == "1":
    time.sleep(30)
    sys.exit(1)
s.sendall(prompt)
line = b""
fg = None  # the running program that has not prompted: "cat" or "spin"
while True:
    b = s.recv(1)
    if not b:
        sys.exit(1)
    if b == b"\x03" and intr:
        s.sendall(b"^C\r\n" + prompt)
        line, fg = b"", None
        continue
    if b == b"\x7f" and rubout:
        if line:
            line = line[:-1]
            s.sendall(b"\x08 \x08")
        continue
    if b != b"\r":
        s.sendall(b)  # echo, as rzsh (and cooked mode) does
        line += b
        continue
    cmd, line = line.decode(), b""
    if fg == "cat":  # cooked mode echoes CR as CR LF; cat writes the line
        s.sendall(b"\r\n" + cmd.encode() + b"\n")
        continue
    s.sendall(b"\r\r\n")
    if fg:
        continue
    if cmd == "exit":
        s.sendall(os.environ.get("FAKE_EXIT", "").encode())
        s.close()
        sys.exit(int(os.environ.get("FAKE_EXIT_RC", "0")))
    if cmd == "cat":
        fg = "cat"
        continue
    if cmd == "spin":
        fg = "spin"
        s.sendall(b"spin: running\r\n")
        continue
    s.sendall(replies.get(cmd, "").replace("\n", "\r\n").encode() + prompt)
"""
QEMU_IMG_STUB = """#!/usr/bin/env bash
for a in "$@"; do last="$a"; done
: > "$last"
"""
MKINITRAMFS_STUB = """import sys
out = sys.argv[sys.argv.index("--output") + 1]
open(out, "wb").close()
"""

REPLIES = {
    "echo hi": "hi\n",
    "pwd": "/\n",
    "ls /bin": "  cat\n  init\n  rzsh\n",
    "cat /etc/motd": "[spawn_args] spawn_args(/bin/cat, argc=2)\nWelcome to Harland!\n",
    "echo after-cat": "after-cat\n",
}
# tty_session()'s commands (#4254), kept apart so the wrong-answer cases above
# stay one per SESSION command.
TTY_REPLIES = {
    "echo abc": "abc\n",
    "echo $?": "130\n",
    "echo still-here": "still-here\n",
}
TTY_PASSES = (
    "PASS: rzsh's line editor",
    "PASS: cooked read(0)",
    "PASS: Ctrl-C kills cat blocked in read(0)",
    "PASS: a command killed by Ctrl-C exits 130",
    "PASS: spin (a program that never ends) starts",
    "PASS: Ctrl-C during a long-running program",
    "PASS: spin killed by Ctrl-C exits 130",
    "PASS: Ctrl-C at the prompt",
    "PASS: rzsh survives Ctrl-C at its prompt",
)
EXIT = ("Goodbye!\r\n[init] Shell exited\r\n"
        "[exit] init exited with code 0, powering off\r\n")
# Before #1882 the kernel took rzsh's exit as init's: no "[init] Shell exited".
EXIT_AS_INIT = "Goodbye!\r\n[exit] init exited with code 0, powering off\r\n"


# --------------------------------------------------------------------------
# Wiring: main.yml and indium's Makefile
# --------------------------------------------------------------------------


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _indices(steps: list[dict], script: str) -> list[int]:
    return [i for i, s in enumerate(steps) if script in str(s.get("run", ""))]


def test_shell_boot_runs_after_the_nvme_boots_and_before_the_log_upload():
    assert (REPO / SHELL_SCRIPT).is_file()
    steps = _build_all()
    [shell] = _indices(steps, SHELL_SCRIPT)
    assert shell > max(_indices(steps, NVME_SCRIPT))
    uploads = [i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads and min(uploads) > shell, "shell.log must be uploaded too"


def test_shell_step_is_a_real_gate_with_a_timeout():
    steps = _build_all()
    [step] = [steps[i] for i in _indices(steps, SHELL_SCRIPT)]
    assert "continue-on-error" not in step
    assert "|| true" not in step["run"]
    assert step.get("timeout-minutes")
    assert "boot-logs" in step["run"]
    assert "SKIP_BUILD" not in step["run"]
    parsed = [s for s in ci_local.load_steps() if SHELL_SCRIPT in s.run]
    assert len(parsed) == 1 and not parsed[0].is_setup


@pytest.mark.integration
def test_make_shell_boots_init_interactive_on_a_serial_stdio_console():
    """`make shell` is the image the boot test scripts: init_interactive as
    /bin/init, COM1 on the terminal, no display."""
    r = subprocess.run(["make", "-n", "-C", str(REPO / "projects/indium"), "shell",
                        "OVMF_CODE=/x/OVMF_CODE.fd"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "--init init_interactive" in r.stdout
    assert "-serial mon:stdio" in r.stdout
    assert "-display none" in r.stdout
    assert "fat:rw:" in r.stdout


def test_readme_says_how_to_get_a_prompt():
    assert "make -C projects/indium shell" in (REPO / "projects/indium/README.md").read_text()


# --------------------------------------------------------------------------
# Verdicts: the script against a stub QEMU
# --------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(REPO / SHELL_SCRIPT, tools / "test_shell_boot.sh")
    shutil.copy(REPO / "projects/harland/tools/shell_session.py", tools / "shell_session.py")
    (tools / "mkinitramfs.py").write_text(MKINITRAMFS_STUB)
    pkgs = root / "projects" / "indium" / "initramfs.pkgs"
    pkgs.parent.mkdir(parents=True)
    pkgs.write_text("indium\nrzsh\n")
    for rel in (
        "projects/harland/build/debug/harland.elf",
        "projects/harland/build/debug/BOOTX64.EFI",
        "projects/indium/build/debug/init.elf",
        "projects/indium/build/debug/init_interactive.elf",
        "projects/rzsh/build/debug/rzsh.elf",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.write_bytes(b"")
    return {"root": root, "script": tools / "test_shell_boot.sh", "stubs": stubs,
            "ovmf": ovmf, "tmp": tmp_path}


def _stub(stubs: Path, name: str, body: str) -> None:
    p = stubs / name
    p.write_text(body)
    p.chmod(0o755)


def _run(tree, *, replies=None, tty_replies=None, qemu=True,
         env_extra=None) -> subprocess.CompletedProcess:
    stubs = tree["stubs"]
    _stub(stubs, "qemu-img", QEMU_IMG_STUB)
    if qemu:
        _stub(stubs, "qemu-system-x86_64", QEMU_STUB)
        path = f"{stubs}{os.pathsep}{os.environ['PATH']}"
    else:
        for tool in ("dirname", "python3"):
            os.symlink(shutil.which(tool), stubs / tool)
        path = str(stubs)
    env = {
        "PATH": path,
        "HOME": str(tree["tmp"]),
        "SKIP_BUILD": "1",
        "BOOT_TIMEOUT": "5",
        "SHELL_TYPE_DELAY": "0",
        "OVMF_CODE": str(tree["ovmf"]),
        "STUB_LOG": str(tree["tmp"] / "stub.log"),
        "FAKE_REPLIES": json.dumps({**(REPLIES if replies is None else replies), **(tty_replies or TTY_REPLIES)}),
        "FAKE_EXIT": EXIT,
        **(env_extra or {}),
    }
    return subprocess.run(["/bin/bash", str(tree["script"])], env=env,
                          capture_output=True, text=True, timeout=90)


@pytest.mark.integration
def test_missing_qemu_is_a_setup_error(tree):
    r = _run(tree, qemu=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-system-x86_64" in r.stderr


@pytest.mark.integration
def test_a_scripted_session_passes(tree):
    keep = tree["tmp"] / "logs"
    keep.mkdir()
    r = _run(tree, env_extra={"KEEP_WORK": str(keep)})
    assert r.returncode == 0, r.stdout + r.stderr
    for cmd in ("echo hi", "pwd", "ls /bin", "cat /etc/motd", "echo after-cat", "exit"):
        assert f"PASS: `{cmd}`" in r.stdout
    for check in TTY_PASSES:
        assert check in r.stdout, check
    assert "FAIL" not in r.stdout
    transcript = (keep / "shell.log").read_text()
    assert "Welcome to Harland!" in transcript and "Goodbye!" in transcript
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "-serial chardev:con" in argv and "-display none" in argv


@pytest.mark.integration
def test_no_prompt_fails(tree):
    """The Tier-1 init (or a renamed prompt) never prompts: main before #4252."""
    r = _run(tree, env_extra={"FAKE_NO_PROMPT": "1", "FAKE_BANNER": "ALL TESTS PASSED\r\n"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: no rzsh prompt" in r.stdout


@pytest.mark.integration
def test_a_different_prompt_fails(tree):
    r = _run(tree, env_extra={"FAKE_PROMPT": "rzsh$ "})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: no rzsh prompt" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize("cmd", list(REPLIES))
def test_a_wrong_answer_fails(tree, cmd):
    replies = dict(REPLIES, **{cmd: "nope\n"})
    r = _run(tree, replies=replies)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"FAIL: `{cmd}`" in r.stdout


@pytest.mark.integration
def test_exit_without_a_power_off_fails(tree):
    r = _run(tree, env_extra={"FAKE_EXIT_RC": "1"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: `exit`" in r.stdout


@pytest.mark.integration
def test_exit_that_skips_init_interactive_fails(tree):
    """rzsh's exit must return to its parent (#1882), not end init itself."""
    r = _run(tree, env_extra={"FAKE_EXIT": EXIT_AS_INIT})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: `exit`" in r.stdout


@pytest.mark.integration
def test_init_exit_before_shell_exited_fails(tree):
    """The order matters: init_interactive reports the shell, then init exits."""
    r = _run(tree, env_extra={"FAKE_EXIT": "Goodbye!\r\n[exit] init exited with code 0, "
                              "powering off\r\n[init] Shell exited\r\n"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: `exit`" in r.stdout


@pytest.mark.integration
def test_no_rubout_fails(tree):
    """DEL taken as a byte: rzsh's editor and cooked mode both fail."""
    r = _run(tree, env_extra={"FAKE_NO_RUBOUT": "1"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: rzsh's line editor" in r.stdout
    assert "FAIL: cooked read(0)" in r.stdout
    assert "PASS: Ctrl-C during a long-running program" in r.stdout


@pytest.mark.integration
def test_ctrl_c_ignored_fails(tree):
    """Ctrl-C that never reaches the foreground program: no prompt comes back."""
    r = _run(tree, env_extra={"FAKE_NO_INTR": "1"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PASS: cooked read(0)" in r.stdout
    assert "FAIL: Ctrl-C kills cat blocked in read(0)" in r.stdout


@pytest.mark.integration
def test_wrong_status_after_ctrl_c_fails(tree):
    r = _run(tree, tty_replies=dict(TTY_REPLIES, **{"echo $?": "0\n"}))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: a command killed by Ctrl-C exits 130" in r.stdout
    assert "FAIL: spin killed by Ctrl-C exits 130" in r.stdout


@pytest.mark.integration
def test_a_kernel_exception_fails(tree):
    r = _run(tree, env_extra={"FAKE_EXIT": EXIT + "!!! EXCEPTION !!! #GP\r\n"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "kernel exception" in r.stdout


def _mkinitramfs(tmp_path, *extra) -> subprocess.CompletedProcess:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "init.elf").write_bytes(b"TIER1")
    (bin_dir / "init_interactive.elf").write_bytes(b"SHELL")
    return subprocess.run([sys.executable, str(REPO / "projects/harland/tools/mkinitramfs.py"),
                           "--bin-dir", str(bin_dir), "--output", str(tmp_path / "i.tar"), *extra],
                          capture_output=True, text=True, timeout=60)


@pytest.mark.integration
@pytest.mark.parametrize("extra, want", [((), b"TIER1"), (("--init", "init_interactive"), b"SHELL")])
def test_mkinitramfs_init_picks_bin_init(tmp_path, extra, want):
    import tarfile
    r = _mkinitramfs(tmp_path, *extra)
    assert r.returncode == 0, r.stdout + r.stderr
    with tarfile.open(tmp_path / "i.tar") as t:
        assert t.extractfile("./bin/init").read() == want
        assert t.extractfile("./bin/init_interactive").read() == b"SHELL"
        assert b"Welcome to Harland!" in t.extractfile("./etc/motd").read()


@pytest.mark.integration
def test_mkinitramfs_unknown_init_is_an_error(tmp_path):
    r = _mkinitramfs(tmp_path, "--init", "nosuch")
    assert r.returncode != 0
    assert "nosuch" in r.stderr
