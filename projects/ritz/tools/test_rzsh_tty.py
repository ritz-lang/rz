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


def test_rzsh_takes_itself_out_of_the_foreground_before_isig_is_on():
    """#4276: rzsh hands the console to its children (sys_tty_setfg) before
    os_tty_suspend turns ISIG back on, so a Ctrl-C typed before spawn starts
    the command is not rzsh's: the kernel drops it instead of killing rzsh."""
    os_code = _code(RZSH_SRC / "os.ritz")
    fg = os_code.split('[[target_os = "harland"]]\nfn os_tty_fg_children')[1]
    fg = fg.split("[[target_os")[0]
    assert "sys_tty_setfg(STDIN, TTY_FG_CHILDREN, 0)" in fg
    suspend = _body(os_code, "os_tty_suspend")
    assert suspend.index("os_tty_fg_children()") < suspend.index("os_disable_raw_mode()")
    # Every time, not once: a nested rzsh (a script) moves it to its own children.
    assert suspend.index("os_tty_fg_children()") < suspend.index("return false")


def test_exec_external_has_the_window_hook():
    """RZSH_DEBUG_TTY_WINDOW stops rzsh in a read(0) between restoring ISIG
    and spawning, so the serial session can type Ctrl-C in that window."""
    ext = _body(_code(RZSH_SRC / "shell.ritz"), "exec_external")
    suspend, hook, spawn = (ext.index(s) for s in
                            ("os_tty_suspend()", "RZSH_DEBUG_TTY_WINDOW", "os_spawn_search("))
    assert suspend < hook < spawn
    assert "os_tty_window_probe()" in ext
