"""tools/ test configuration: load ritz0's spawn_guard (AGAST #4092).

`make tools-unit` runs `pytest tools/`, which never reads ritz0/conftest.py,
so AGAST #1805's rule (a test that starts a process must be `integration`)
went unenforced here: 454 unmarked tools/ tests spawned on 2026-11-18.  With
the guard loaded, an unmarked tools/ test that starts a process fails, naming
the command, and `-m "not integration"` really is the no-subprocess tier for
tools/ too.  tools/test_tools_spawn_guard.py checks this stays loaded.

ritz0/ and ritz0/harness/ (where spawn_guard lives, AGAST #3915) are
appended to sys.path (not prepended) so no tools/ module is shadowed.  In a mixed session (`pytest ritz0/tests/x.py tools/y.py`) both
conftests name the plugin, and pytest registers it once.
"""

import sys
from pathlib import Path

_RITZ0 = Path(__file__).resolve().parent.parent / "ritz0"
for _dir in (str(_RITZ0), str(_RITZ0 / "harness")):
    if _dir not in sys.path:
        sys.path.append(_dir)

pytest_plugins = ["spawn_guard"]
