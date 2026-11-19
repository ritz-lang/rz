"""rzsh hands the harland console to the commands it runs (AGAST #4254).

On harland, rzsh's raw mode is a real sys_tty_setattr that turns off echo,
canonical mode and ISIG while it edits a line; exec_external restores the
saved attributes while the command runs and takes raw mode back afterwards.
So Ctrl-C at the prompt is a byte for the editor, and Ctrl-C during a
command reaches the command (the kernel kills it with status 130).

The kernel side lives in ritz0/test_harland_tty.py. This check reads rzsh's
sources, so it lives here, outside the ritz0 step's scope (#4032).
"""

import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
RZSH_SRC = WORKSPACE / "projects" / "rzsh" / "src"


def _code(path):
    """The file's code with comments stripped."""
    return "\n".join(
        line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines()
    )


def _body(code, name):
    """The text of `fn name` up to the next top-level line."""
    m = re.search(rf"^(?:pub )?fn {name}\(.*?(?=^\S)", code + "\nEND", re.S | re.M)
    assert m, f"fn {name} not found"
    return m.group(0)


def test_raw_mode_is_a_real_tty_setattr_on_harland():
    os_code = _code(RZSH_SRC / "os.ritz")
    raw = os_code.split('[[target_os = "harland"]]\npub fn os_enable_raw_mode')[1]
    raw = raw.split("[[target_os")[0]
    assert "sys_tty_setattr" in raw and "TTY_ISIG" in raw


def test_exec_external_hands_the_terminal_to_the_command():
    ext = _body(_code(RZSH_SRC / "shell.ritz"), "exec_external")
    assert "os_tty_suspend()" in ext and "os_tty_resume(" in ext
